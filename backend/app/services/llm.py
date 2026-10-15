"""Provider-agnostic LLM client for the analysis pipeline.

The pipeline never imports a vendor SDK directly; it talks to this small
`generate(system, user, model)` surface. Two real backends implement it:

- BedrockClient  — AWS Bedrock Converse API (default). One code path serves
  any Converse-capable model (Amazon Nova, Anthropic Claude, Llama, ...),
  so switching models is an env-var change. Also satisfies the Amazon
  "AWS Builder" mini challenge (bedrock:InvokeModel at runtime).
- NebiusClient   — OpenAI-compatible Token Factory endpoint, for the Nebius
  hackathon. Selected only when LLM_PROVIDER=nebius.

In MOCK_MODE the factory returns None and each pipeline stage produces a
deterministic simulated result, so the whole app runs with no keys
(CLAUDE.md section 2.6).

Security (CLAUDE.md 12.2, 12.7):
- Outbound TLS is always verified (never verify=False); every call has a
  timeout and a bounded max_tokens.
- Secrets are never placed in prompts; callers mask message content first
  (see pipeline/sanitize.py).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Protocol, runtime_checkable

import httpx

from app.config import Settings

logger = logging.getLogger("faro")

# Hard ceilings shared by every backend.
_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 30.0


class LLMError(Exception):
    """Raised when a provider call fails or returns an unusable response."""


@runtime_checkable
class LLMClient(Protocol):
    async def generate(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        """Return the model's text output, or raise LLMError."""
        ...


def parse_json_object(text: str) -> dict:
    """Extract and parse the first JSON object from a model's text output.

    Models sometimes wrap JSON in markdown fences or add prose. We take the
    substring from the first '{' to the last '}' and parse it. The result is
    still validated against a Pydantic schema by the caller, so a wrong shape
    is rejected downstream (CLAUDE.md 12.7, structured output).
    """
    fenced = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    start = fenced.find("{")
    end = fenced.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMError("No JSON object found in model output.")
    try:
        obj = json.loads(fenced[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError("Model output was not valid JSON.") from exc
    if not isinstance(obj, dict):
        raise LLMError("Model output was not a JSON object.")
    return obj


class BedrockClient:
    """AWS Bedrock Converse backend. boto3 is synchronous, so calls run in a
    worker thread to avoid blocking the event loop."""

    def __init__(self, *, region: str, access_key: str, secret_key: str) -> None:
        # Imported lazily so the dependency is only needed when Bedrock is used.
        import boto3
        from botocore.config import Config

        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                connect_timeout=_CONNECT_TIMEOUT,
                read_timeout=_READ_TIMEOUT,
                retries={"max_attempts": 2, "mode": "standard"},
            ),
        )

    def _converse(
        self, *, system: str, user: str, model: str, max_tokens: int, temperature: float
    ) -> str:
        response = self._client.converse(
            modelId=model,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        try:
            return response["output"]["message"]["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected Bedrock Converse response shape.") from exc

    async def generate(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        try:
            return await asyncio.to_thread(
                self._converse,
                system=system,
                user=user,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 — provider/network errors
            # Never log the prompt (may contain the analyzed message).
            logger.warning("Bedrock call failed: %s", type(exc).__name__)
            raise LLMError("Bedrock call failed.") from exc


class NebiusClient:
    """OpenAI-compatible Token Factory backend (Nebius hackathon)."""

    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def generate(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        timeout = httpx.Timeout(_READ_TIMEOUT, connect=_CONNECT_TIMEOUT)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            logger.warning("Nebius call failed: %s", type(exc).__name__)
            raise LLMError("Nebius call failed.") from exc


def get_llm_client(settings: Settings) -> LLMClient | None:
    """Return the configured LLM client, or None in MOCK_MODE.

    A None return means "simulate": each pipeline stage then produces a
    deterministic stand-in instead of calling a provider.
    """
    if settings.mock_mode:
        return None

    if settings.llm_provider == "nebius":
        return NebiusClient(
            base_url=settings.nebius_base_url,
            api_key=settings.nebius_api_key,
        )

    # Default: Bedrock.
    return BedrockClient(
        region=settings.effective_bedrock_region,
        access_key=settings.aws_access_key_id,
        secret_key=settings.aws_secret_access_key,
    )
