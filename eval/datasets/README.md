# Evaluation datasets

## `sample.jsonl` (bundled)

A small, balanced set of **synthetic** messages written for this project by
the Faro team. It contains no real personal data and is released under the
same MIT license as the repository, so it can be committed and shared freely.

Each line is a JSON object:

```json
{ "text": "…", "label": "scam" | "legit", "note": "optional" }
```

It is intentionally small — enough to exercise the evaluation harness and
demonstrate the metrics end to end without spending model credits. It is
**not** a benchmark; the numbers it produces are illustrative.

## Larger public datasets (not bundled)

For a fuller evaluation, drop additional `*.jsonl` files (same schema) into
`eval/datasets/raw/` (gitignored) and pass `--data` to `run_eval.py`. Good
public sources for phishing / smishing research include the UCI SMS Spam
Collection and public phishing-email corpora. Record the source and license
of anything you add here, and do not commit datasets whose license forbids
redistribution.
