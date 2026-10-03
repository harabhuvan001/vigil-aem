# Bootstrap validation report

Verified on 2026-10-03 in `D:\PAPER 1\vigil-aem`. Status: **environment/bootstrap phase**.
No scientific claims are made. The source repository tree is in REPOSITORY_TREE.txt; ignored
runtime environments, caches, tracking files, and Git internals are intentionally excluded.

## Machine inspection before changes

| Item | Observed |
|---|---|
| OS | Windows 11 Home Single Language, 10.0.26200 |
| Architecture | x64 |
| Working directory | D:\PAPER 1\vigil-aem |
| Git | 2.55.0.windows.3 |
| Existing Python | 3.14.8 and 3.12.3 |
| Node / npm | v24.21.0 / 12.2.0 |
| Docker CLI / Compose | 29.6.2 (dfc4efb) / v5.3.1 |
| RAM | 16,478,712 KiB total; 315,768 KiB free at initial inspection |
| C: disk | 267,249,512,448 bytes total; 18,422,009,856 bytes initially free |
| D: disk | 243,551,694,848 bytes total; 92,272,525,312 bytes initially free |
| GPU | Intel UHD Graphics; no nvidia-smi; torch.cuda.is_available() returned False |
| Existing PostgreSQL client | 17.2; libpq-fe.h already present |
| Git state | Empty root, not initially a Git repository; initialized in this root on setup/research-environment |

Docker's Linux daemon was initially stopped. `docker desktop start` succeeded. The bootstrap
did not replace existing Python, Git, Node, npm, curl, PostgreSQL client, Docker, or Codex.

## Installed tools and dependencies

- uv 0.12.22, installed with the official Astral PowerShell installer.
- uv-managed CPython 3.11.17; project targets the Python 3.11 series.
- GNU Make 4.4.1, jq 1.8.2, GNU Wget 1.21.4, GCC/G++ 15.2.0 installed through user-level Scoop.
- Codex CLI 0.159.3 was already present and was verified; no authentication was attempted.

Requested runtime dependencies and resolved installed versions:

```text
numpy==2.4.6
pandas==3.0.6
scipy==1.17.1
pydantic==2.13.5
pyyaml==6.0.3
python-dotenv==1.2.4
rich==15.0.0
tenacity==9.1.4
scikit-learn==1.9.1
xgboost==3.2.0
statsmodels==0.15.0
torch==2.14.1
transformers==5.18.0
sentence-transformers==6.1.0
openai==3.24.0
sqlalchemy==2.1.3
psycopg==3.3.6
psycopg-binary==3.3.6
pgvector==0.5.0
mlflow==3.16.1
```

Development dependencies:

```text
pytest==9.1.1
pytest-cov==7.1.0
ruff==0.16.10
mypy==2.4.0
types-PyYAML==6.0.12.20260906
```

All 19 requested runtime dependency imports succeeded without API keys or model downloads.
The complete transitive dependency graph is recorded in uv.lock; Windows sync checked 142
installed packages and the universal lock resolved 164 package entries.

## Validation results

| Check | Observed result |
|---|---|
| uv sync | Passed |
| uv lock --check | Passed |
| make lint | Ruff check passed; all 62 Python files formatted |
| make typecheck | Passed; no issues in 41 source files |
| make test | 62 passed; last full run took 5.72 seconds |
| Bash syntax checks | All five shell helpers passed |
| scripts/check_environment.sh via Git Bash | Exit 0; all required tools present |
| docker compose config --quiet | Passed |
| docker compose up -d --wait | Passed; PostgreSQL healthy |
| scripts/start_services.sh | Passed; returned pgvector 0.8.1 |
| PostgreSQL runtime | PostgreSQL 17.8; loopback 127.0.0.1:5433 |
| pgvector extension | vector 0.8.1 installed |
| Vector operation | '[1,2,3]' <-> '[1,2,4]' returned 1 |
| MLflow tracking | Successful FINISHED smoke run, dummy parameter/metric and provenance artifact verified |
| Tracked artifact audit | No .env, .envrc, virtual environment, model binaries, or bytecode tracked |
| git diff --check | Passed |

Verified PostgreSQL image digest:
`pgvector/pgvector@sha256:3e8b3adfd27b5707128f60956f62a793c3c9326ea8cfaf0eab7adccb5d700b21`.

Successful MLflow smoke run: `e4ff270f897247349abbe3741c9ab0cb`.
It logged project VIGIL-AEM, Python 3.11.17, Git commit
`2937a77fa513200b68f0dfb3cef7815c5ccc8843`, seed 42, dummy_parameter=bootstrap,
dummy_metric=1.0, and provenance.json. The portability fix was uncommitted during that smoke run;
the recorded commit identifies the repository base, not an immutable snapshot of that run's
entire working tree. This is an infrastructure smoke record, not a research result.
A Windows stdout encoding failure on the first attempt was fixed by explicitly selecting UTF-8
in the smoke entry point; the subsequent run completed successfully.

MLflow shut down through Ctrl+C with application-shutdown completion confirmed. PostgreSQL
remains running for local development. Tracking files and artifacts remain ignored locally.
The optional mock API Compose configuration was validated statically; its container was not
started during bootstrap.

## Git work

Development branch: `setup/research-environment`. No merge or push was performed.
Logical commits before the documentation commit:

- `0c834e0` chore: initialize reproducible Python research environment
- `5ba2160` chore: add Docker PostgreSQL and pgvector services
- `0c17c17` feat: add core research schemas and deterministic sandbox skeleton
- `2937a77` test: add bootstrap and reproducibility tests
- `bd66170` fix: make bootstrap scripts portable across Windows and Bash

The documentation commit is titled `docs: add research architecture and experiment protocol`.
Its identifier can be obtained with `git log -1 --oneline`; it cannot be embedded in its own contents.

## Limitations and owner actions

- Chocolatey installation failed because this session cannot write its administrative package
  directory. A user-level Scoop installation succeeded, so the requested Windows tools are present.
- build-essential and libpq-dev are Linux package names and were not installed on Windows.
  GCC/G++/Make and the pre-existing PostgreSQL client headers supply the relevant native equivalents.
- direnv and nvidia-smi are absent and optional. No CUDA GPU was verified.
- MLflow's job execution backend is unsupported on Windows; normal local tracking was verified.
  A third-party Starlette WSGI deprecation warning did not prevent tracking.
- The existing Codex executable is an npm cache shim. If removed, install a durable global CLI
  using `npm install -g @openai/codex@latest`.
- Restart terminals to pick up user PATH additions for uv and Scoop tools.
- Complete `codex login` interactively if needed, following CODEX_SETUP.md.
  Never put credentials in the repository or chat.
- Configure future API/database secrets through the environment or Devin Settings > Secrets.
  No secrets are needed for the current tests.
- direnv users can inspect/copy .envrc.example to .envrc and run direnv allow.
- Implement SkillShiftBench v0.1 and the no-memory versus similarity-memory baseline next;
  research entry points and learned components are intentionally unimplemented.
