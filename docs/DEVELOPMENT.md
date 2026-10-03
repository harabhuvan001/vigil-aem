# Development

Use the existing project root; never create a nested duplicate repository. Work on development
branches and do not push directly to main. Run `git status` before edits and `make check` before commits.

## Python and quality tools

Python is pinned to the 3.11 series in `.python-version` and `pyproject.toml`; the bootstrap
machine installed 3.11.17 through uv. `uv.lock` pins the resolved dependency graph.
Use `uv sync --locked` for repeatable installs. No Conda or global Python libraries are needed.

```sh
bash scripts/setup.sh
make lint
make format
make typecheck
make test
make test-cov
make check
uv run --locked python scripts/export_schemas.py
```

PowerShell equivalents are `uv run --locked ruff check .`,
`uv run --locked ruff format --check .`, `uv run --locked mypy`, and `uv run --locked pytest`.
GNU Make recipes use portable executable commands. Shell helpers require Bash (Git Bash on
Windows; WSL is not required).

## System prerequisites

On Debian/Ubuntu, install missing packages only:

```sh
sudo apt-get update
sudo apt-get install git curl wget jq build-essential gcc g++ make libpq-dev postgresql-client
```

Install Node/npm, Docker CLI/Compose and Codex only when missing, using their platform-supported
installers. `build-essential` and `libpq-dev` are Linux package names; on Windows a GCC/Make
toolchain and existing PostgreSQL client headers are the relevant equivalents. Psycopg uses
binary wheels, so native compilation is not required for the current locked environment.
No system package should be replaced merely to match a Linux command.

The environment checker treats Python 3.11, uv, Git, GNU Make, Node, npm, and Codex as required
for the complete workflow. Docker daemon, DB connectivity, GPU and native build helpers are
optional for default tests. It does not print environment secrets or DATABASE_URL.

## Environment and Devin

`.env.example` contains placeholders only. Set DATABASE_URL and OPENAI_API_KEY later through
your secret manager when needed. The default tests and smoke fixtures need neither.
Configuration loads a small explicit environment overlay for seed, log level and MLflow URI;
it does not silently load credential files.

Devin supports direnv. The owner can copy `.envrc.example` to `.envrc`, inspect it, and run
`direnv allow`. Never commit `.envrc`. For later Devin credentials, use
**Devin Settings > Secrets**, not chat or source files. Windows direnv is optional.

## PostgreSQL and optional mock API

```sh
docker compose config
make services-up
make services-down
docker compose --profile mock-api up -d --wait
```

PostgreSQL binds to 127.0.0.1:5433; local placeholder user/database are `vigil_dev`.
The clearly non-production password is a Compose fallback only. Override POSTGRES_USER,
POSTGRES_PASSWORD, POSTGRES_DB and POSTGRES_PORT through environment variables for another
local configuration. Never use these development defaults in production.
The SQLAlchemy connection format is `postgresql+psycopg://USER:PASSWORD@127.0.0.1:5433/DATABASE`.
Do not commit an instantiated connection string.

The init SQL creates pgvector on an empty development volume. For a pre-existing volume, run
`CREATE EXTENSION IF NOT EXISTS vector;` interactively with an appropriately privileged local
user. `docker compose down` preserves data; the scripts do not delete volumes.
The optional API exposes /health (200), /503, and /401; it uses the Python standard library.
The deterministic retry experiment uses the in-memory sandbox, not this external service.

If Docker cannot execute in a hosted Devin environment, run static Compose validation and
document the failure; do not claim runtime DB verification.

## Local MLflow

`make mlflow` runs a loopback server on http://localhost:5000 with ignored local SQLite metadata
and artifact storage. Equivalent:

```sh
uv run --locked mlflow server --host 127.0.0.1 --port 5000 --workers 1 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts
# In a second terminal:
uv run --locked python experiments/smoke_mlflow.py
```

Stop the server with Ctrl+C. The smoke experiment logs project, Python, commit (if available),
seed, a dummy parameter, dummy metric, and provenance. It explicitly labels itself as an
infrastructure test. Tracking data and database files are ignored.

## Next milestone

Specify SkillShiftBench v0.1, frozen task/skill family splits and versioned prompts, then implement
no-memory versus similarity-memory baselines. Do not treat planned experiment entry points as
implemented baselines. Follow EXPERIMENT_PROTOCOL.md.
