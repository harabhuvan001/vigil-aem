# Phase 1 compliance: SkillShiftBench v0.1

This record covers the authorized deterministic benchmark foundation only. PASS means the
specified implementation was inspected or its stated verification completed successfully.
Infrastructure tests are not research-performance observations. Future baseline evaluation,
family splits, prompts and models are outside this task and are not marked as implemented.

## Verification evidence

- E1: Repository guidance, architecture, experiment protocol, existing schemas, sandbox modules
  and all existing tests were read before implementation. Base commit: `492d571`.
- E2: `git branch --show-current`: `experiment/skillshift-v0.1`; created from the existing
  `setup/research-environment` checkout. No merge operation was performed; no local main branch
  exists. Existing architecture/modules were preserved.
- E3: `uv sync --locked` completed; runtime Python is `3.11.17`; no dependencies were added.
- E4: `uv run --locked python scripts/skillshift_benchmark.py`: 40 skills, 200 targets,
  200 reset fixtures; each domain has 10 skills and 50 targets; integrity and SHA256 PASS.
- E5: `uv run --locked pytest tests/unit/test_skillshift_data.py
  tests/integration/test_skillshift_fixtures.py -x -q`: **483 passed**. The initial run emitted
  two expected serializer warnings from intentionally corrupt records; tests now explicitly
  assert those warnings. Ground truth was not changed to resolve execution failures.
- E6: `make lint`: Ruff check PASS and format check PASS (73 Python files formatted).
- E7: `make typecheck`: mypy PASS, 48 source files checked.
- E8: Final `make lint typecheck test check` exited **0**: Ruff lint/format PASS, mypy PASS,
  **545 tests passed in 392.46 seconds**, with no warnings. This invokes all requested targets
  and the required aggregate check, with each Make dependency executed once. Make reports
  nothing further to do for `check` because its lint/typecheck/test dependencies already passed
  in that invocation. All 62 existing tests and 483 new benchmark tests passed.
- E9: Diff review preserves bootstrap schema definitions, toy fixtures, all planned research
  modules, `uv.lock`, and `configs/experiments.yaml` (publication epsilon remains null).
- E10: `git diff --cached --check` passed; staged JSONL bytes were compared with working-tree
  bytes and all three SHA256 digests, with equality confirmed before commit.

## Requirement matrix

Paths are relative to the repository root. U denotes `tests/unit/test_skillshift_data.py`;
I denotes `tests/integration/test_skillshift_fixtures.py`. A named test covers all parameterized
records unless a subset is explicitly indicated.

| Requirement | Implementation path | Verification method/evidence | Status |
|---|---|---|---|
| Read required files first; continue existing repository | `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/EXPERIMENT_PROTOCOL.md`, existing code/tests | E1; inspected current contracts and all existing tests before edits | PASS |
| Use requested experiment branch | Repository branch | E2 | PASS |
| Do not redesign repository | `src/vigil/benchmark/`, benchmark-specific sandbox drivers | E9; additive code, existing bootstrap behavior unchanged | PASS |
| Build deterministic foundation only | `src/vigil/benchmark/`, `src/vigil/sandbox/skillshift*.py` | E5; finite authored actions and inspectable state | PASS |
| No LLM agent | Existing `src/vigil/agent/` unchanged | E9; no inference call in new code | PASS |
| No harm predictor | Existing `src/vigil/governor/risk.py` unchanged | E9; remains planned | PASS |
| No VIGIL governor | Existing `src/vigil/governor/` unchanged | E9; no new policy behavior | PASS |
| No AEM | Existing `src/vigil/aem/` unchanged | E9; no new memory update behavior | PASS |
| No uncertainty model | New deterministic benchmark code only | E9; inspected diff, no estimator added | PASS |
| No external benchmark | Authored `src/vigil/benchmark/catalog.py` | E9; synthetic data, no external dataset fetched | PASS |
| Exactly four requested domains | `src/vigil/benchmark/schema.py:Domain` | E4; U `test_counts_domains_ids_and_categories` | PASS |
| Filesystem domain exists | Catalog `fs_*`; filesystem fixture driver | E4/E5; 10 skills and 50 targets | PASS |
| Mock HTTP/API domain exists | Catalog `api_*`; in-process handlers | E4/E5; 10 skills and 50 targets | PASS |
| SQL/database domain exists | Catalog `sql_*`; SQLite driver | E4/E5; 10 skills and 50 targets | PASS |
| Git operations domain exists | Catalog `git_*`; temporary repository driver | E4/E5; 10 skills and 50 targets | PASS |
| Exactly 40 source skills | `benchmark/skills/skills_v0.1.jsonl` | E4; U count assertion | PASS |
| Exactly 10 source skills per domain | Skills JSONL and integrity validator | E4; per-domain Counter equals 10 | PASS |
| Exactly one EXACT target per source | `benchmark/transfer_tasks/skillshift_v0.1.jsonl` | U category Counter equals enum for every source | PASS |
| Exactly one NEAR target per source | Targets JSONL | Same U category completeness check | PASS |
| Exactly one NEUTRAL target per source | Targets JSONL | Same U category completeness check | PASS |
| Exactly one NEGATIVE target per source | Targets JSONL | Same U category completeness check | PASS |
| Exactly one DECEPTIVE target per source | Targets JSONL | Same U category completeness check | PASS |
| Exactly 200 target tasks | Targets JSONL | E4; U count equals 40 times 5 | PASS |
| Deterministic ground truth for every task | Catalog, target oracle, domain drivers | E5; I `test_all_finite_actions_ground_truth_and_deterministic_reset` enumerates allowed actions for all 200 tasks | PASS |
| Task contains task_id | `schema.py:TransferTask`, targets JSONL | U roundtrip, required-field and unique-ID tests | PASS |
| Task contains source_skill_id | Same task schema/data | U required-field test; integrity rejects missing references | PASS |
| Task contains domain | Same task schema/data | U required-field and invalid-domain tests | PASS |
| Task contains transfer_category | Same task schema/data | U required-field, invalid-category and completeness tests | PASS |
| Task contains natural_language_goal | Same task schema/data | U required-field and nonempty-goal tests | PASS |
| Task contains initial_state | Same task schema/data | U required-field test; I initial snapshot equality | PASS |
| Task contains allowed_actions | Same task schema/data | U nonempty/finite/unique-action tests; I finite-action enumeration | PASS |
| Task contains expected action or accepted action set | `TransferTask.accepted_actions` | U required/nonempty/subset checks; I action oracle agreement | PASS |
| Task contains expected_final_state | Same task schema/data | U missing-outcome rejection; I full-state equality | PASS |
| Task contains deterministic reward rules | `TransferTask.reward_rules`, `skillshift.py:score` | U invalid-rule rejection; I `test_reward_requires_accepted_action_and_entire_state` for 200 tasks | PASS |
| Task contains severity_if_failed | Same task schema/data | U rejects nonfinite/out-of-range/non-numeric values; I checks severity | PASS |
| Task contains fixture/reset identifier | `TransferTask.fixture_id`, `Fixture.reset_id` | U required-field and invalid-reset tests; E5 all referenced fixtures reset | PASS |
| Task contains metadata | `schema.py:Metadata`, targets JSONL | U required-field and roundtrip; family/operation validation | PASS |
| Skill contains skill_id | `schema.py:SourceSkill`, skills JSONL | U required-field, roundtrip and unique-ID validation | PASS |
| Skill contains domain | Same skill schema/data | U required-field, domain balance and source-context agreement | PASS |
| Skill contains goal | Same skill schema/data | U required-field and JSONL model validation | PASS |
| Skill contains preconditions | Same skill schema/data | U required-field; nonempty typed list in all 40 skills | PASS |
| Skill contains ordered procedure | `SourceSkill.procedure` | U required-field and ordered list roundtrip | PASS |
| Skill contains postconditions | Same skill schema/data | U required-field and nonempty typed list | PASS |
| Skill contains source_task_id | Same skill schema/data | U required-field; integrity rejects duplicate source IDs | PASS |
| Skill contains source_context | `schema.py:SourceContext` | U required-field; source EXACT fixture/state/action agreement | PASS |
| Skill contains provenance | `schema.py:Provenance` | U required-field and all-record roundtrip; synthetic origin/version/seed | PASS |
| Skill contains version | `SourceSkill.version`, skills JSONL | All 40 stored records contain fixed version 0.1; U roundtrip | PASS |
| Use Pydantic schemas | `src/vigil/benchmark/schema.py`, `benchmark/schemas/skillshift_*.json` | U all-record validation and exported schema equality | PASS |
| Store benchmark in JSONL | Three versioned benchmark JSONL files | U parses every line and verifies canonical reserialization | PASS |
| Deterministic fixtures for all domains | `benchmark/fixtures/skillshift_v0.1.jsonl`, sandbox drivers | E5; all 200 initial/action/reset/replay cases pass | PASS |
| Filesystem uses only temporary directories | `SkillShiftFixture.reset`, `_path` | I owned-root assertions; host sentinel/confinement test; U rejects traversal/absolute paths | PASS |
| SQL uses disposable/resettable state | `SkillShiftFixture.reset`, `_apply_sql` | I connect guard permits only `:memory:`; reset equality for all SQL targets | PASS |
| Git uses only temporary repositories | `skillshift_git.py:_GitRepository` | I owned-root assertions and subprocess cwd/config guard | PASS |
| Mock API is deterministic/local/in-process | `SkillShiftFixture._apply_api` | I socket blocker and all API reset/action/replay checks | PASS |
| Integrity checks 40 skills and 200 targets | `dataset.py:validate_integrity` | U count and count-corruption tests | PASS |
| Integrity checks five categories per source | Same validator | U completeness and duplicate-category corruption test | PASS |
| Integrity checks unique IDs | Same validator | U duplicate skill/source/target/fixture corruption tests | PASS |
| Integrity checks valid skill references | Same validator | U missing-skill corruption test | PASS |
| Integrity checks valid domains | Schema and integrity validator | U invalid-domain, source-context and per-domain count checks | PASS |
| Integrity checks reset fixture exists | Fixture map and operation catalog | U missing-fixture/unknown-operation/state corruption; E5 executable resets | PASS |
| Integrity checks reward rule exists | Required Pydantic reward contract | U missing-reward and invalid-rule tests | PASS |
| Integrity checks expected outcome exists | Required typed outcome contract | U missing-outcome and required-field tests | PASS |
| Integrity checks severity values | Strict finite [0,1] field | U severity boundaries and corruption tests | PASS |
| Generate SHA256 checksums | `benchmark/skillshift_v0.1.sha256` | E4; U `test_checksums_and_regeneration_are_byte_reproducible` and tamper detection | PASS |
| Update benchmark README | `benchmark/README.md` | Inspected paths, commands, counts and scope against E4/E5 | PASS |
| Document purpose | `docs/SKILLSHIFT_V0_1.md` | Purpose and component mapping sections inspected | PASS |
| Document benchmark structure | Same specification | Corpus structure and file/reference contracts inspected | PASS |
| Document domains | Same specification | Four-domain operation/environment table inspected against catalog | PASS |
| Document transfer categories | Same specification | Five-category definition table inspected against data | PASS |
| Document deterministic ground truth | Same specification | Exact action/state reward and snapshot contract inspected against tests | PASS |
| Document limitations | Same specification | Explicit synthetic/macros/no-comparison limits recorded | PASS |
| Explain need for synthetic control | Same specification | Controlled confounders and disposable mutations explained | PASS |
| Tests for schemas | U | E5; roundtrip, required fields, invalid contracts, schema export checks | PASS |
| Tests for benchmark counts | U | E5; total and per-domain assertions | PASS |
| Tests for category completeness | U | E5; all 40 source groups checked | PASS |
| Tests for deterministic reset | I | E5; all 200 tasks replayed after reset | PASS |
| Tests for reward rules | I | E5; finite allowed actions and entire-state scoring | PASS |
| Tests for checksum reproducibility | U | E5; reconstructed bytes/hash equality and tamper detection | PASS |
| Tests for no access to real files/databases | U/I | E5; path rejection, host sentinel, in-memory connection and network/config guards | PASS |
| Run make lint | Makefile lint target unchanged | E6 | PASS |
| Run make typecheck / mypy | Makefile typecheck target unchanged | E7 | PASS |
| Run make test (entire repository) | Makefile test target unchanged | E8; 545 tests passed | PASS |
| Run make check before commit | Makefile aggregate target unchanged | E8; all aggregate dependencies passed before commit | PASS |
| Record requirement, path, verification and status | This file | Every requirement row has all four columns and completed evidence | PASS |
| Do not merge to main | Experiment branch only | E2/E9; no merge performed | PASS |
| Map components before research behavior | Specification component table | E1 and initial specification written before code; hypothesis/experiment/metric/ablation recorded | PASS |
| Preserve ground truth and publication epsilon | Frozen corpus builder; existing experiment configuration | U refuses changed-file overwrite; E9 epsilon remains null | PASS |
| No credentials, tracking artifacts, experiment outputs or dependency changes | Scoped repository additions; unchanged lockfile | E9 diff inspection; release JSONL files are authorized benchmark inputs | PASS |

## Remaining failures

None. All required checks passed before commit. The corpus is a deterministic synthetic
foundation; future model evaluation, evaluation splits, and research methods remain unimplemented
as documented in the specification and are outside the current authorization.
