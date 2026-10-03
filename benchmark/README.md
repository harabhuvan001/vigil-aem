# Benchmark foundation

SkillShiftBench v0.1 contains **40 synthetic source skills and 200 target tasks**, with exactly
10 skills and 50 targets in each of four domains. Each skill has one EXACT, NEAR, NEUTRAL,
NEGATIVE, and DECEPTIVE target. Every outcome is inspectable and deterministic. These are
benchmark specifications and infrastructure checks, not observed LLM performance or publication
results. See [the specification](../docs/SKILLSHIFT_V0_1.md) and
[phase-one compliance](../docs/PHASE_1_COMPLIANCE.md).

| File | Contents |
|---|---|
| `skills/skills_v0.1.jsonl` | 40 versioned skills; each embeds its source task context and unique source task ID |
| `transfer_tasks/skillshift_v0.1.jsonl` | 200 targets, complete expected logical states, accepted actions, rewards and severity |
| `fixtures/skillshift_v0.1.jsonl` | 200 reset descriptors with deterministic operation IDs and initial states |
| `skillshift_v0.1.sha256` | SHA256 of the exact bytes of all three JSONL files |
| `schemas/skillshift_*.json` | Public JSON schemas exported from the canonical Pydantic contracts |

The source task context references the corresponding EXACT reset fixture; source task IDs are
distinct from target task IDs. Source contexts are embedded, so there is no additional source
task corpus to join. The older six `fixtures/toy_cases.json` smoke cases and bootstrap schemas
remain separate, unchanged illustrative infrastructure examples.

Filesystem actions operate only in owned temporary directories. SQLite connections use
`:memory:` only. API actions use fixed in-process handlers without sockets. Git actions use
owned temporary repositories, fixed identities/dates, isolated configuration, and disabled hooks.
No fixture accepts a caller-supplied directory, database connection, URL, or shell command.
Git must be installed; no external service or credential is required.

Validate the frozen release:

```sh
uv sync --locked
uv run --locked python scripts/skillshift_benchmark.py
make lint
make typecheck
make test
```

Rebuild into a separate review directory and compare bytes:

```sh
uv run --locked python scripts/skillshift_benchmark.py --build --root /path/to/review-directory
uv run --locked python scripts/export_schemas.py
```

The builder uses authored specifications, seed 0, stable ordering and canonical UTF-8/LF JSONL.
It refuses to overwrite changed existing release files. Git attributes preserve hashed bytes
across platforms. Never change ground truth after viewing test-set model performance; corrections
require a new auditable release. The corpus has no evaluation split or model runs yet. Frozen
family splits, versioned prompts, pinned models, and paired provenance must precede future
baseline evaluation under [the experiment protocol](../docs/EXPERIMENT_PROTOCOL.md).
