# Assumptions

These are design assumptions or expected hypotheses, not observed research results.

- Procedural skill reuse can have positive, neutral, or negative transfer under distribution shift.
- Inspectable preconditions should be checked deterministically; semantic interpretation may require LLMs.
- Independent paired environments can support counterfactual comparisons for controlled toy tasks.
- Adverse evidence may help reduce repeated consequential failures; its benefit must be measured.
- Python 3.11, uv.lock, seeded CPU toy execution, and explicit provenance provide a usable
  reproducibility foundation. External API determinism is not assumed.
- A loopback PostgreSQL/pgvector service and local MLflow are sufficient initial infrastructure.
- Local database defaults are publicly documented non-production placeholders.
- MIT is used for bootstrap source; external datasets/model weights need their own license review.
- The source tree uses standard `__init__.py` package files (the request's `init.py` spelling
  is interpreted as Python package initialization).
