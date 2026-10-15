"""Evaluate Faro against a naive single-pass baseline.

Faro's claim is that a layered pipeline with a deterministic floor beats a
single model call. This script measures that on a labeled dataset, reporting
precision, recall, F1 and the false-positive rate for the "scam" class, and
writes a results table for the README.

Usage:
    python eval/run_eval.py                 # MOCK_MODE, bundled sample set
    python eval/run_eval.py --data path.jsonl
    python eval/run_eval.py --real          # use the configured LLM (needs keys)

Dataset format: JSON Lines, one object per line with "text" and "label"
("scam" | "legit"). See eval/datasets/README.md.

The baseline:
  - with --real: a single LLM call that answers scam/not-scam with no checks,
    no evidence and no floor.
  - in MOCK_MODE: a naive keyword classifier, standing in for an un-grounded
    single pass. The point is the contrast with Faro's grounded pipeline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Make the backend package importable when run from the repo root.
_BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_BACKEND))

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE / "datasets" / "sample.jsonl"
RESULTS_DIR = HERE / "results"

# A fixed trusted circle for evaluation, so look-alike detection has real
# brands to compare against (mirrors a user who registered common CR brands).
EVAL_TRUSTED = [
    {"kind": "bank", "name": "BAC Credomatic", "domains": ["baccredomatic.com"]},
    {"kind": "bank", "name": "Banco Nacional", "domains": ["bncr.fi.cr"]},
    {"kind": "company", "name": "Kolbi", "domains": ["kolbi.cr"]},
    {"kind": "company", "name": "Netflix", "domains": ["netflix.com"]},
    {"kind": "company", "name": "SINPE", "domains": ["sinpe.fi.cr"]},
]

_BASELINE_KEYWORDS = (
    "http",
    "codigo",
    "code",
    "gift",
    "premio",
    "prize",
    "urgente",
    "urgent",
    "cripto",
    "crypto",
    "cvv",
    "password",
)


@dataclass
class Metrics:
    precision: float
    recall: float
    f1: float
    fpr: float
    n: int

    def row(self, name: str) -> str:
        return (
            f"| {name:<22} | {self.precision:6.2f} | {self.recall:6.2f} "
            f"| {self.f1:6.2f} | {self.fpr:6.2f} |"
        )


def _metrics(y_true: list[bool], y_pred: list[bool]) -> Metrics:
    tp = sum(t and p for t, p in zip(y_true, y_pred, strict=True))
    fp = sum((not t) and p for t, p in zip(y_true, y_pred, strict=True))
    fn = sum(t and (not p) for t, p in zip(y_true, y_pred, strict=True))
    tn = sum((not t) and (not p) for t, p in zip(y_true, y_pred, strict=True))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return Metrics(precision, recall, f1, fpr, len(y_true))


def _baseline_mock(text: str) -> bool:
    folded = text.lower()
    return any(k in folded for k in _BASELINE_KEYWORDS)


def load(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


async def evaluate(data_path: Path, real: bool) -> dict:
    os.environ.setdefault("ENVIRONMENT", "development")
    if not real:
        os.environ["MOCK_MODE"] = "true"
        os.environ.setdefault("MODEL_EXTRACT", "mock")
        os.environ.setdefault("MODEL_VERDICT", "mock")

    from app.config import get_settings
    from app.pipeline.pipeline import analyze
    from app.pipeline.schemas import TrustedEntity

    settings = get_settings()
    trusted = [TrustedEntity(**t) for t in EVAL_TRUSTED]

    rows = load(data_path)
    y_true = [r["label"] == "scam" for r in rows]
    faro_pred: list[bool] = []
    base_pred: list[bool] = []

    for r in rows:
        result = await analyze(r["text"], trusted, settings, language="es")
        # Faro flags scam when risk is medium or high (fail toward caution).
        faro_pred.append(result.risk_level in ("medium", "high"))
        base_pred.append(_baseline_mock(r["text"]))

    faro = _metrics(y_true, faro_pred)
    base = _metrics(y_true, base_pred)

    table = "\n".join(
        [
            f"Dataset: {data_path.name} — {len(rows)} messages "
            f"({sum(y_true)} scam, {len(rows) - sum(y_true)} legit)",
            "",
            "| System                 | Prec.  | Recall |   F1   |  FPR   |",
            "| ---------------------- | ------ | ------ | ------ | ------ |",
            faro.row("Faro (full pipeline)"),
            base.row("Baseline (single pass)"),
        ]
    )
    return {
        "dataset": data_path.name,
        "n": len(rows),
        "faro": faro.__dict__,
        "baseline": base.__dict__,
        "table": table,
        "real": real,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Faro vs a baseline.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--real", action="store_true", help="use the configured LLM")
    args = parser.parse_args()

    out = asyncio.run(evaluate(args.data, args.real))
    print(out["table"])

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / "latest.json"
    result_file.write_text(json.dumps(out, indent=2, ensure_ascii=False), "utf-8")
    print(f"\nSaved results to {result_file.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
