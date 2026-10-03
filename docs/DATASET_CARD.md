# Bootstrap dataset card

**Name:** VIGIL-AEM deterministic infrastructure toy fixtures
**Version:** bootstrap-0.1
**Purpose:** verify schemas, deterministic action execution, state reset, and paired-run infrastructure.
**Research status:** illustrative examples; not a publication benchmark and not evidence of transfer.

## Contents and provenance

Six hand-authored synthetic cases in `benchmark/fixtures/toy_cases.json`: HTTP 503 retry,
HTTP 401 retry, temporary-file deletion, protected-backup deletion attempt, transaction-valid
update, and update without the required transaction. They contain no personal information,
real credentials, live URLs, or production database records. Licensed under repository MIT terms.

Rewards (+1 success, -1 failure) and severity (0 or 1) are explicit toy conventions, not calibrated
consequential-harm estimates. The protected-file attempt is marked severe but blocked in memory.
The SQL cases are state-machine fixtures, not SQL parser/execution validation.

No training/validation/test splits, real procedural skills, LLM annotations, or measured
distribution shifts exist yet. Source, transfer, and adverse-event directories are placeholders.
Before SkillShiftBench v0.1, specify task/skill families, split manifests, annotation rules,
reward definitions, licenses, decontamination, and frozen ground truth.
