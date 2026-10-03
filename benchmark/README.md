# Benchmark foundation

Only six deterministic infrastructure fixtures exist in `fixtures/toy_cases.json`.
They are illustrative examples, not publication results or SkillShiftBench v0.1.
See [dataset card](../docs/DATASET_CARD.md). Pydantic schema exports are in `schemas/`;
regenerate with `uv run --locked python scripts/export_schemas.py`.

The source_tasks, transfer_tasks, and adverse_events directories are placeholders. Future
benchmark development must freeze ground truth, family splits, annotation provenance and licenses.
