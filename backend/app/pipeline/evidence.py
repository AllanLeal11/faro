"""Evidence stage: optional live search (Tavily) for corroboration.

This stage looks *about* the sender — the official domain of the claimed
organization and any scam reports tied to a suspicious domain or number. It
is optional: when no Tavily key is configured the stage is skipped and the
pipeline marks the result `partial` (CLAUDE.md section 4, robustez).

Security (CLAUDE.md 12.6, 12.7):
- Faro never fetches a URL taken from the message. Tavily receives search
  *queries* (org names, domains, numbers), never a URL to visit, and never
  the user's personal data.
- Tavily results are UNTRUSTED. Only https source URLs are kept, and the
  text is passed downstream as data, never as instructions.
"""

from __future__ import annotations

import logging

import httpx

from app.pipeline.schemas import EvidenceItem, Extraction

logger = logging.getLogger("faro")

_TAVILY_URL = "https://api.tavily.com/search"
_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 15.0
_MAX_RESULTS = 3


def _build_queries(extraction: Extraction) -> list[str]:
    """Build a small set of safe search queries from extracted, non-personal
    fields only."""
    queries: list[str] = []
    if extraction.claimed_sender:
        queries.append(f"{extraction.claimed_sender} official website domain")
    # De-duplicate suspicious domains, cap to keep credit/latency bounded.
    for domain in list(dict.fromkeys(extraction.domains))[:2]:
        queries.append(f"{domain} scam report OR phishing")
    return queries[:3]


async def search_evidence(
    extraction: Extraction, api_key: str, base_id: int = 0
) -> list[EvidenceItem]:
    """Return search-based evidence items, or [] if unavailable.

    `base_id` offsets evidence ids so they don't collide with the check ids
    (chk-*). Search ids are "ev-*".
    """
    if not api_key:
        return []

    queries = _build_queries(extraction)
    if not queries:
        return []

    items: list[EvidenceItem] = []
    counter = base_id
    timeout = httpx.Timeout(_READ_TIMEOUT, connect=_CONNECT_TIMEOUT)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for query in queries:
                resp = await client.post(
                    _TAVILY_URL,
                    json={
                        "api_key": api_key,
                        "query": query,
                        "max_results": _MAX_RESULTS,
                        "search_depth": "basic",
                        "include_answer": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                for result in data.get("results", [])[:_MAX_RESULTS]:
                    url = result.get("url", "")
                    # Keep only https sources (CLAUDE.md 12.5, safe links).
                    if not isinstance(url, str) or not url.startswith("https://"):
                        continue
                    counter += 1
                    title = str(result.get("title", ""))[:200]
                    items.append(
                        EvidenceItem(
                            id=f"ev-{counter}",
                            kind="search",
                            type="search",
                            result="source",
                            detail=title or "Search result",
                            source_url=url,
                        )
                    )
    except (httpx.HTTPError, ValueError) as exc:
        # Degrade gracefully: the pipeline continues on checks alone.
        logger.warning("Evidence stage failed: %s", type(exc).__name__)
        return items

    return items
