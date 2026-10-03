# Fast prototype compliance and evidence

This audit distinguishes implementation/execution compliance from support for a research
hypothesis. A completed experiment can leave a hypothesis unsupported or inconclusive.
Generated results and models remain local and ignored, as required by `AGENTS.md`.

The experiment contract was committed before measured execution in `427449f`. The benchmark,
policy, reward, embedding revision, family splits, models, and threshold selection rules were
not changed after viewing outcomes. Phase 1 ground truth is unchanged from `6fdc4cf`.
Publication epsilon remains unset. No LLM credentials were found by presence-only checks of
supported provider variables and local configuration; no secret values were printed.

Independent artifact validation passed: 200 core pairs, 2132 raw execution rewards recomputed, nine required PNGs decoded, and every system/control outcome linked to the ledger. The final test rerun passed all 774 tests; lint and mypy also passed. Metrics are not inferred from category labels.

| Requirement | Implementation path | Verification method / evidence | Status |
|---|---|---|---|
| Read guidance, Phase 1 documentation, data, schemas, tests, existing environments | `AGENTS.md`; `docs/PHASE_1_COMPLIANCE.md`; `docs/SKILLSHIFT_V0_1.md`; `benchmark/`; `src/vigil/sandbox/` | Preflight inspection; existing 545-test suite passed before implementation, `results/final_prototype/phase1_tests.txt` | PASS |
| One working branch; do not modify main | `experiment/vigil-fast-prototype` | `git branch --show-current`; original Phase 1 commit retained | PASS |
| A: Phase 1 counts, categories, identities, references, deterministic outcomes, SHA256 | `benchmark/dataset.py`; `scripts/skillshift_benchmark.py` | Corpus validator PASS: 40 skills, 200 targets, 200 fixtures; 10 skills / 50 targets in each of four domains; fixture action tests | PASS |
| Preserve ground truth; disclose genuine fixes | `benchmark/*.sha256`; all Phase 1 JSONL/schema files | `git diff 6fdc4cf -- benchmark schemas` is empty; no bug or new benchmark version required | PASS |
| B: shared reset, observe, execute, evaluate, clone contract | `sandbox/skillshift.py` | Existing action/reset tests and new independent verification tests; actual execution verified by ledger/artifact audit | PASS |
| B: filesystem owns temporary resources and protects scope boundaries | `sandbox/skillshift.py`; `benchmark/schema.py` | Host sentinel, traversal, symlink, teardown tests; all 50 filesystem task actions exercised | PASS |
| B: deterministic in-process mock API, no external ground-truth calls | `sandbox/skillshift.py`; `benchmark/catalog.py` | No-network test; all Phase 1 API operations/statuses exercised; arbitrary HTTP is not exposed | PASS |
| B: disposable SQL, deterministic transactions and constraints | `sandbox/skillshift.py` | SQLite `:memory:` only, primary-key constraint and transaction scope; host database sentinel and all 50 task tests | PASS |
| B: disposable Git with isolated config/hooks and protected context | `sandbox/skillshift_git.py`; `evaluation/prototype_schema.py` | Temporary repository/config isolation and all 50 Git task tests; no arbitrary repository argument | PASS |
| C: environment-derived reward, no LLM judge | `sandbox/skillshift.py:score` | Frozen Phase 1 +1/-1 reward; accepted action and complete final state equality; reward tests and all raw rewards recomputed by artifact validator | PASS |
| D: all 200 same-agent WITH/WITHOUT pairs; identical initial state hashes | `agent/policy.py`; `evaluation/prototype.py` | 200 same-state core pairs; exposure/hash/reward audit PASS | PASS |
| E: deterministic benchmark policy labeled accurately | `agent/policy.py`; `prompts/deterministic_policy_v1.txt` | Literal goal policy tests, oracle-field poisoning tests; generated measured reports validated | PASS |
| F: inspect secure provider configuration; run LLM only if available | `evaluation/run_prototype.py` | Presence-only inspection found no configured credentials; real LLM experiment not executed | PASS |
| G: real pinned Sentence Transformers cosine, correlation/category/trap analysis | `skills/embeddings.py`; `configs/fast_prototype.json` | All 8,000 task/skill goal cosines and 200 paired values; actual cosine/correlation/category artifacts validated | PASS |
| H: applicability with satisfied, violated, unknown facts; S0/S1/S2 comparison | `governor/applicability.py`; `evaluation/prototype.py` | Bounded score and per-domain factual gate tests; all S0-S8 comparisons executed and validated | PASS |
| I: factual normalized shift score, explicit unknowns | `governor/shift.py` | Signal/bounds tests; measured feature artifact validated; no universal-optimality claim | PASS |
| J: measured-only labels, eight features, historical execution provenance | `evaluation/prototype.py`; `governor/risk.py` | Labels recomputed from paired rewards; no category/oracle model inputs; artifact audit PASS | PASS |
| J: source-skill grouped train/validation/test with split checksum | `configs/fast_prototype_splits.json`; `scripts/freeze_fast_split.py` | Frozen 12 fit / 12 calibration / 8 validation / 8 test families; all variants stay together; split and test-label poisoning tests | PASS |
| K: majority, logistic regression, random forest, XGBoost; validation-only selection | `governor/risk.py` | Fitted model, feature schema, binary/multiclass metrics and confusion matrices verified by artifact audit | PASS |
| L: native/sigmoid/isotonic calibration, Brier/ECE/reliability, validation thresholds | `governor/risk.py`; `governor/policy.py` | Separate calibration-training families; frozen selection artifact audit PASS | PASS |
| M: S3/S4/S5; independent uncertain verification, retention/frequency/runtime | `evaluation/prototype.py`; `sandbox/skillshift.py` | VERIFY acceptance/rejection unit controls in all domains; actual S3–S5 metrics verified | PASS |
| N: validated AdverseExperienceMemory fields, admission, relevance and priority | `aem/memory.py`; `evaluation/prototype.py:event_from_pair` | Bounds/noncausal admission tests; paired evidence and replay event factors recomputed from actual execution IDs | PASS |
| O: compare no AEM, naive failure, severity-only, full causal/reliability AEM | `evaluation/prototype.py` | S5–S8 executed trials and AEM comparison recomputed from control trials | PASS |
| P: exact, related, similar-safe, unrelated prospective controls | `evaluation/prototype.py` | Separately identified forced-source seeds and all four control types verified by artifact audit; never pooled with core pairs | PASS |
| Q: FRR, CFA, OAR, PTR, success, NTR, mean gain | `evaluation/prototype.py:summarize_aem` | Metrics recomputed from control trials; zero denominators stay null; audit PASS | PASS |
| R: complete S0–S8 ablation with null/negative findings retained | `evaluation/prototype.py`; `evaluation/reporting.py` | All-corpus descriptive and held-out tables verified by artifact audit | PASS |
| S: clustered bootstrap CI, paired permutation, McNemar, effects and caveats | `evaluation/statistics.py` | Seeded repeatability unit test; measured `statistics.json` validated; no deterministic population significance claim | PASS |
| T: human-readable measured report, OBSERVED / INTERPRETATION / LIMITATION | `evaluation/reporting.py` | `FINAL_RESULTS.md` generated from artifacts; audit PASS | PASS |
| U: concise supervisor text summary | `evaluation/reporting.py` | `EXECUTIVE_SUMMARY.txt` generation/consistency audit PASS | PASS |
| V: nine required publication-resolution PNG figures | `evaluation/reporting.py` | All nine PNGs decoded/nonempty, 300-dpi export; contact sheet visually inspected | PASS |
| W: raw/paired/features/prediction Parquet, CSV/JSON/provenance/checksum outputs | `evaluation/run_prototype.py` | Mandatory artifact validator PASS | PASS |
| X: self-contained local HTML report with all figures | `evaluation/reporting.py` | Required figure references and no server/network dependencies; audit PASS | PASS |
| Y: terminal summary populated from measured artifacts | `evaluation/run_prototype.py:print_summary` | `experiment_terminal.txt` completed; all fields read from summary/table artifacts | PASS |
| Z: claims have metrics, artifacts, limitations and evidence-based status | `evaluation/reporting.py`; `docs/CLAIMS_AND_EVIDENCE.md` | Claims generated from measured outcomes; audit PASS | PASS |
| Final: lint, typecheck, tests and make check | `Makefile`; `tests/` | make lint/typecheck/test/check PASS; 774 tests passed in 462.41 seconds; results/final_prototype/final_validation_checks.txt | PASS |
| Final: benchmark/result validation; all plots/reports/raw outputs nonempty | `scripts/validate_prototype_results.py` | Independent artifact/reward recomputation PASS | PASS |
| Final: secrets/resources/Git diff; no merge or generated-artifact commit | `.gitignore`; finite sandbox drivers | Tracked credential/model/result filename scan clear; sandbox sentinel/config/network tests PASS; final Git audit PASS | PASS |

Scope: all **existing Phase 1** finite action macros are executable. This does not add arbitrary
shell, SQL, HTTP, or Git tools, or unrepresented stress cases such as Git merge/stash, arbitrary
HTTP 403/404/409/429/500, or externally connected databases. Protected scopes are explicit task
constraints rather than operating-system security boundaries. The refusal to expose arbitrary
resources is intentional and preserves the frozen benchmark contract.

Scientific adequacy is assessed separately in `CLAIMS_AND_EVIDENCE.md`: absent beneficial
transfer, a perfect deterministic gate, collapsed AEM weights, or zero-recurrence floors cannot
establish the full proposed method. Shared cross-domain task templates remain a leakage/generalization
limitation even with disjoint source skill IDs. No test results or ground truth are changed to
remove these limitations.

Paths such as `governor/` and `evaluation/` above are relative to `src/vigil/`. Final audit outputs are `results/final_prototype/artifact_validation.json` and `repository_audit.json`. The frozen selection and raw trial artifacts remain available locally.

## Observed adequacy limits

Measured core label counts: `{"HARM": 49, "NEUTRAL": 151}`. No HELP opportunities means PTR is NOT AVAILABLE, not zero. Factual preconditions already eliminated observed harmful reuse; predictors/uncertainty/verification did not add held-out outcome improvement over that gate. In the prospective controls S5 and S6-S8 all had FRR=0 and OAR=0; AEM added safe verification in 25% of those control trials without additional recurrence reduction. Causal score and diagnosis confidence were one in all admitted events, so full weighting did not distinguish itself from severity-only memory. These findings limit the research claim, not the execution audit.

A result-validator defect was discovered after execution: undefined PTR was represented as Python None in recomputed tables and NaN in CSV, causing NumPy comparison to fail. The comparison now normalizes only the missing-value representation, with a regression test that rejects replacing an undefined value with zero. Reports were regenerated from existing artifacts to expose paired confidence intervals and held-out component differences. No policy, benchmark, reward, fitted model, split, threshold, raw ledger, paired result or held-out prediction changed. Measurement provenance remains commit `427449f`; subsequent changes are reporting, validation, tests and documentation only.
