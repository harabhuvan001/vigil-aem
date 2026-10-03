# VIGIL-AEM

**Status: environment/bootstrap phase. No scientific claims are made yet.**

> Can an autonomous LLM agent predict when reusing a previously learned procedural skill will
> improve or harm performance under distribution shift?

VIGIL-AEM studies risk-aware continual learning for LLM agents: predicting HELP, NEUTRAL, or HARM
from procedural reuse, with Adverse Experience Memory (AEM) intended to reduce repeated
consequential failures. This repository currently supplies schemas, reproducibility utilities,
in-memory toy sandboxes, a paired counterfactual runner, and development infrastructure.

The planned architecture retrieves skills, checks preconditions and shift, consults history and
AEM, predicts risk, chooses USE / VERIFY / REJECT, executes in a sandbox, and evaluates paired
counterfactual outcomes. Learned retrieval, predictors, agent reasoning, and memory updates are
**planned and unvalidated**. See [architecture](docs/ARCHITECTURE.md).

## Setup

Install Git, Python via [uv](https://docs.astral.sh/uv/getting-started/installation/), and GNU Make.
Node/npm and Codex are required for the coding-agent workflow. Docker is optional for core tests.

```sh
uv python install 3.11
uv sync --locked
make check
bash scripts/check_environment.sh
```

On Windows, use Git Bash for shell scripts and GNU Make, or invoke the uv commands directly in
PowerShell. See [development](docs/DEVELOPMENT.md) for prerequisites and platform notes.
No API key, model download, or running database is needed for tests.

## Services and smoke tracking

```sh
docker compose up -d --wait
docker compose exec -T postgres psql -U vigil_dev -d vigil_dev -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
make mlflow
# In another terminal:
uv run --locked python experiments/smoke_mlflow.py
docker compose down
```

MLflow runs at http://localhost:5000. The smoke script logs only explicitly synthetic
infrastructure values. Stop the foreground server with Ctrl+C. PostgreSQL defaults are
non-production placeholders and bind only to loopback, on port 5433 to avoid an existing local
PostgreSQL installation. The optional mock API uses the `mock-api` Compose profile.

## Repository

- `src/vigil/`: agent schemas, skills, governor stubs, AEM schemas, sandboxes, evaluation, utilities.
- `configs/`: validated defaults and future model/experiment placeholders.
- `benchmark/`: versioned toy fixtures and schema exports; no publication benchmark yet.
- `experiments/`: six explicitly unimplemented research entry points and an MLflow smoke test.
- `tests/`: deterministic unit and local integration checks.
- `docs/`: architecture, protocol, dataset card, assumptions, limitations, setup and validation.
- `scripts/`: setup, environment checks, service controls, and test helpers.
- `analysis/`, `data/`, `results/`: placeholders; generated data and results are ignored.

## Codex and safety

Start `codex` from this repository root. Owner login is interactive; see
[Codex setup](docs/CODEX_SETUP.md). Future agents must follow [AGENTS.md](AGENTS.md).

Never commit credentials or generated artifacts. Use local environment variables or Devin
Settings > Secrets. The toy sandboxes operate on in-memory state only; do not connect experimental
actions to real accounts, production databases, or protected files.

The next research milestone is SkillShiftBench v0.1 and the no-memory versus similarity-memory
baseline. See [experiment protocol](docs/EXPERIMENT_PROTOCOL.md) before implementation.
