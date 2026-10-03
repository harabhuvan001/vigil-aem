# SkillShiftBench v0.1 deterministic foundation

This version defines a synthetic, controlled corpus for future studies of negative procedural
transfer. It implements ground truth and fixture execution only. It contains no LLM agent,
retrieval baseline, harm predictor, VIGIL governor, AEM, uncertainty model, or external benchmark.
No comparative research results have been observed. Publication epsilon remains unset.

## Component mapping (recorded before implementation)

| Component | Expected hypothesis | Future experiment | Metric | Ablation |
|---|---|---|---|---|
| Versioned skills and five target contexts | Context changes can make procedural reuse inappropriate | Future paired no-memory versus similarity-memory study | Paired reward delta by category and skill family | Remove skill access |
| Independent resettable fixtures | Identical initial states prevent carryover from explaining a paired difference | Replay and reset infrastructure checks; later paired runs | State equality and replay equality | Deliberately shared mutable state in a test-only sensitivity check |
| Exact state and action reward | Inspectable outcomes permit reproducible success labels | Exhaustive finite-action oracle checks | Oracle agreement and severity on failure | Action-only versus full-state scoring in a future analysis |
| Integrity checks and byte hashes | Frozen inputs make changes auditable | Rebuild and tamper checks | Counts, reference validity, SHA256 equality | Omit hash verification in a test-only corruption check |

These are proposed hypotheses and infrastructure contracts, not validated scientific claims.

## Corpus structure and domains

The release has 40 source skills, 10 per domain. Exactly five targets reference each skill,
giving 200 targets, 50 per domain and 40 per transfer category. Three versioned JSONL files
store skills, targets, and 200 reset descriptors. The source task (unique `source_task_id`,
initial/expected state, allowed/expected action, and reset fixture) is embedded in each skill's
`source_context`. Its reset descriptor is shared with its EXACT target. Provenance identifies
synthetic authorship, specification, generator version, MIT license, and seed 0. No randomness
or model revision is involved in corpus construction.

| Domain ID | Ten source operations | Mutable environment |
|---|---|---|
| `filesystem` | create, write, append, copy, move, delete, mkdir, rmdir, truncate, token replacement | Real files in an owned `TemporaryDirectory` |
| `mock_http_api` | GET, POST, PUT, PATCH, DELETE, 503 retry, token refresh, conditional PUT, redirect, pagination | Fixed in-process handlers and detached API state |
| `sql_database` | insert, update, delete, increment, clear, rename, copy, swap, flag, account transfer | Disposable SQLite `:memory:` table; transactions for mutations |
| `git_operations` | stage, unstage, commit, create/delete branch, switch branch, create/delete tag, restore, remove tracked file | Local temporary repositories with fixed identity and timestamps |

These domain IDs are the four canonical enum values. They describe filesystem, mock HTTP/API,
SQL/database, and Git operations respectively. There are no additional benchmark domains.
Each operation has an independently authored initial and completed state and a finite action
implementation. Two scopes provide distinct resources: filesystem directories, API namespaces,
SQL partitions, or independent local Git repositories.

## Transfer categories

| Category | Controlled change | Accepted actions | Intended interpretation |
|---|---|---|---|
| EXACT | Source operation, primary scope, and preconditions retained | `apply_primary` | Direct reuse is applicable |
| NEAR | Primary absent; equivalent operation requires rebinding to secondary | `apply_secondary` | Small contextual adaptation is required |
| NEUTRAL | Primary is already in its completed state | `apply_primary`, `noop` | Guarded reuse and doing nothing have identical outcomes |
| NEGATIVE | Primary is reserved; secondary alone is authorized | `apply_secondary` | Blind source-bound execution changes a protected resource |
| DECEPTIVE | Same reserved-primary constraint with a stale legacy display alias suggesting primary | `apply_secondary` | Surface resemblance conflicts with authoritative goal constraints |

The goal explicitly names the operation, scope, and preservation constraints. DECEPTIVE hints
are deliberately resolvable, not ambiguous hidden annotations. The difference between NEGATIVE
and DECEPTIVE is the misleading textual cue; their execution state and oracle intentionally
match. These categories are **expected design conditions**, not observed HELP/NEUTRAL/HARM labels
or empirical reward deltas for an LLM. NEAR has no reward claim about unadapted reuse.

The action vocabulary is `apply_primary`, `apply_secondary`, and `noop`. Each apply action is
an inspect-and-apply macro for the fixture's named operation: skip if completed, act only on
the authored pre-state, and reject unexpected pre-states or absent scopes. Domain code performs
the actual mutation; it never copies a target's expected state into the fixture. The completed
source specification is used only for the idempotence guard. The source procedure additionally
requires checking authorization, which future agents must interpret. The fixture deliberately
permits an apply action on a reserved scope so inappropriate reuse is observable and scoreable
inside owned disposable resources. This implements no governor or agent policy.

## Deterministic ground truth and rewards

Each target includes all requested identity/reference fields, a natural-language goal, typed
initial state, allowed and accepted actions, a complete expected final state, the versioned
reward contract, finite severity, fixture ID, and metadata. Skills record domain, goal,
preconditions, ordered procedure, postconditions, source task/context, provenance and version.
Strict Pydantic contracts reject unknown fields and invalid paths, domains, categories or
severities; integrity validation also catches corruption of mutable nested containers.

`exact_action_and_state_v1` gives +1 only if an allowed, accepted action executes and the entire
logical state equals the authored expected outcome; otherwise it gives -1. There is no partial
credit or learned judge. Success severity is zero. Failure severity is 0.25 for EXACT/NEAR/NEUTRAL
and 1.0 for NEGATIVE/DECEPTIVE (synthetic specification weights, not estimates of real-world loss).
Severity is a task-level penalty on **every** failure, including a no-op; it is not a measured
damage score. Reward and severity are separate. All untouched scopes must match exactly.

Snapshots include filesystem file contents/directories, API resources/status/token/etag/cursor/
location, SQL rows, and Git worktree/index contents plus branch/tag names, HEAD and commit-message
history. Git's base file contents are immutable setup provenance. Random temporary paths,
platform-specific file metadata, Git object IDs and physical database internals are excluded
from logical state equality. Git hashes are not research outcomes. API status 0 means no request
has been completed; it is a local sentinel, not an HTTP response code.

Every scored action starts from the task's initial state. Reset destroys/recreates owned state,
including SQLite connections and temporary repositories. Snapshots and descriptors are copied;
independent environments cannot carry mutation across conditions. Tests enumerate every allowed
action in all 200 targets and replay an accepted action after reset. These are oracle/replay
infrastructure checks, never model-performance results.

## Freeze, validation, and reproducibility

Canonical serialization uses sorted keys, catalog/category order, UTF-8 without BOM, and LF
line endings. `benchmark/skillshift_v0.1.sha256` commits exact byte hashes of skills, targets and
fixture descriptors. `.gitattributes` prevents checkout newline rewriting of hashed files.
`scripts/skillshift_benchmark.py` validates counts, per-domain balance, unique skill/source/target/
fixture IDs, five categories per skill, references, operation/domain agreement, reset handlers,
reward and expected outcome contracts, and severities. It verifies SHA256 separately.

`--build --root <review-directory>` reproducibly reconstructs the corpus. Changed existing release
files are never overwritten. Genuine annotation corrections require a new dataset version and
evaluation disclosure. The specification and authored catalog define ground truth before any
model evaluation. The Pydantic schema export command is documented in `benchmark/README.md`.

The corpus is frozen but **unpartitioned** (`metadata.split=unassigned`). No train/validation/test
manifest, prompts, retrieval store, model selection, or paired LLM run is implemented or claimed.
Before comparative work, preregister splits by procedural family, including cross-domain analogues,
freeze prompts and model revisions, log paired provenance and seeds, and follow
`EXPERIMENT_PROTOCOL.md`. A random row split would leak these closely related templates.
Publication epsilon remains null in `configs/experiments.yaml`.

Future agent-facing task views must omit oracle fields, transfer category annotations and
target-derived provenance. The complete evaluator records here must not be fed to retrieval,
training or agent prompts. This foundation does not implement that future presentation boundary.

## Why synthetic control is required

The future question concerns procedural reuse under changed constraints. Controlled variants let
the researcher hold the operation fixed while changing a binding, completion state, authorization,
or misleading cue. Exact inspectable states separate task success from unsupported subjective
judgment and make oracle errors testable. Disposable resources let inappropriate reuse produce
real local mutations without affecting user data or services. Uncontrolled external tasks would
add changing permissions, network state, hidden state and non-reproducible annotations that could
confound a paired transfer comparison.

## Limitations

- Forty authored operation families and repetitive two-scope templates cover a small synthetic
  space. Their analogues are correlated; 200 targets are not 200 independent skill families.
- Finite macro actions restrict plans and tool use. Idempotence guards deliberately simplify
  repeated execution. Ordered procedures are descriptive source records, not an implemented agent.
- The mock API omits transport, concurrency and production authentication. SQLite does not model
  PostgreSQL deployment. Git actions have no remotes, merges or conflicts. Filesystem snapshots
  omit permissions, symlinks, ownership and timestamps.
- NEGATIVE and DECEPTIVE isolate authorization/binding mistakes. They do not establish that
  semantic retrieval actually causes harmful reuse or that any proposed mitigation works.
- The fixtures are not security sandboxes for arbitrary hostile Python or concurrent tampering.
  Only the finite benchmark actions are supported; paths and commands are constrained, user Git
  configuration/hooks are disabled, and no external databases or network are accessed.
- No baseline evaluation, calibrated risk model, uncertainty estimate, external benchmark
  validation or publication claim is supplied by this foundation.
