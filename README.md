# VIGIL-AEM

**Status: deterministic prototype; no generative LLM experiment.**

> Can an autonomous LLM agent predict when reusing a previously learned procedural skill will
> improve or harm performance under distribution shift?

VIGIL-AEM studies risk-aware continual learning for LLM agents: predicting HELP, NEUTRAL, or HARM
from procedural reuse, with Adverse Experience Memory (AEM) intended to reduce repeated
consequential failures. SkillShiftBench-v0.1 supplies 40 source skills and 200 deterministic
targets across filesystem, mock API, SQL, and Git. The fixed-policy pipeline executes paired
trials, compares classical harm predictors, and evaluates governance and AEM ablations.

The planned architecture retrieves skills, checks preconditions and shift, consults history and
AEM, predicts risk, chooses USE / VERIFY / REJECT, executes in a sandbox, and evaluates paired
counterfactual outcomes. The implemented experiment uses benchmark-linked candidates and a
deterministic policy. It does not establish LLM behavior or generalization. See
[architecture](docs/ARCHITECTURE.md), the frozen
[analysis plan](docs/FAST_PROTOTYPE_PROTOCOL.md), and
[claims and evidence](docs/CLAIMS_AND_EVIDENCE.md).

## Measured prototype

```sh
uv sync --locked
make check
uv run --locked python scripts/skillshift_benchmark.py
uv run --locked python experiments/fast_prototype.py --output results/reproduction
uv run --locked python scripts/validate_prototype_results.py --root results/reproduction
```

The experiment downloads a pinned public Sentence Transformers embedding model if uncached.
It does not call a generative model or external ground-truth API. Reports, raw executions,
fitted model, split/checksum manifests, and nine PNG figures are saved locally in the selected
output directory. Open `report.html` directly. Generated results and models remain ignored by
Git. Use a fresh output directory, or `--resume` only with identical source/configuration.
Undefined metrics are reported as `NOT AVAILABLE`; reports distinguish observations from
interpretations and limitations.

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

- `src/vigil/`: schemas, deterministic policy, governor, AEM, sandboxes, evaluation, utilities.
- `configs/`: validated defaults, frozen prototype configuration and source-skill splits.
- `benchmark/`: frozen synthetic SkillShiftBench-v0.1 and bootstrap fixtures; no external benchmark.
- `experiments/`: measured fast prototype, six planned research entry points, and MLflow smoke test.
- `tests/`: deterministic unit and local integration checks.
- `docs/`: architecture, protocol, dataset card, assumptions, limitations, setup and validation.
- `scripts/`: setup, environment checks, service controls, and test helpers.
- `analysis/`, `data/`, `results/`: placeholders; generated data and results are ignored.

## Codex and safety

Start `codex` from this repository root. Owner login is interactive; see
[Codex setup](docs/CODEX_SETUP.md). Future agents must follow [AGENTS.md](AGENTS.md).

Never commit credentials or generated artifacts. Use local environment variables or Devin
Settings > Secrets. The benchmark sandboxes own temporary directories and repositories or
in-memory state; do not connect actions to real accounts, production databases, or user files.

Further research requires a configured, fixed LLM and a benchmark that can measure beneficial
transfer as well as harm. See [experiment protocol](docs/EXPERIMENT_PROTOCOL.md) before extending
the prototype. The publication epsilon remains unset.
