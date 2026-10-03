# Architecture

Status: **deterministic prototype**. SkillShiftBench-v0.1 and a fixed-policy experimental
pipeline are implemented. No autonomous LLM agent has been evaluated. The exploratory experiment
contract and hypothesis/metric/ablation mapping are frozen in
[FAST_PROTOTYPE_PROTOCOL.md](FAST_PROTOTYPE_PROTOCOL.md). Measured conclusions and their limits
are recorded in [CLAIMS_AND_EVIDENCE.md](CLAIMS_AND_EVIDENCE.md).

```text
Task
→ Candidate Skill Retrieval
→ Preconditions
→ Distribution Shift
→ Historical Evidence
→ Adverse Experience Memory
→ Harm/Risk Prediction
→ USE / VERIFY / REJECT
→ Sandbox if needed
→ Execution
→ Counterfactual Evaluation
→ Memory Update
```

## Component contract

| Component | Hypothesis to test (expected, not observed) | Future experiment | Metric | Ablation |
|---|---|---|---|---|
| Retrieval | Similarity selects useful procedural candidates | 02 vs 01 | Paired reward delta, retrieval recall | No retrieval/memory |
| Preconditions | Inspectable constraints prevent invalid reuse | 03 vs 02 | Invalid reuse rate, reward | Remove precondition gate |
| Shift evidence | Context changes identify transfer risk | 04 feature study | Harm recall, calibration | Remove shift features |
| Historical evidence | Prior outcomes add predictive signal | 04 feature study | Calibration, harm precision | Remove historical features |
| AEM | Adverse experiences reduce repeated consequential failures | 06 vs 05 | Severity-weighted recurrence | Disable AEM |
| Harm/risk predictor | Risk estimates improve reuse decisions | 04 vs 03 | AUROC, calibration, paired reward | Similarity-only decision |
| Verification/policy | Verification trades cost for avoided harm | 05 vs 04 | Severe failure rate, verification cost | USE/REJECT only |
| Counterfactual evaluator | Paired execution identifies transfer direction | All comparisons | Delta and confidence intervals | Unpaired analysis as sensitivity check |

These are proposed mappings, not validated claims. Preregister exact metrics, costs, decision rules,
and ablations before evaluating a frozen test set. Update this table as hypotheses change.

## Implemented foundation

- `agent/base.py`, `skills/schema.py`, `aem/schema.py`: Pydantic data contracts.
- `governor/applicability.py`: literal boolean facts only; missing/ambiguous facts fail closed.
- `sandbox/`: independent copy/reset, HTTP retry fixture, dictionary filesystem, transaction
  precondition fixture. These simulations are not security sandboxes for arbitrary code.
- `agent/executor.py`: executes an explicitly provided allowed action.
- `evaluation/counterfactual.py`: independently constructs/reset two environments, checks equal
  initial state, re-seeds each condition, and records WITH_SKILL / WITHOUT_SKILL.
- `utils/`: validated configuration, seed logging, and environment/package/Git/model provenance.

The original numbered experiment entry points 01–06 remain planned. The separate
`experiments/fast_prototype.py` entry point executes the authorized deterministic experiment:

- `benchmark/`: frozen 40-skill, 200-target JSONL corpus with executable reset fixtures.
- `agent/policy.py`: fixed goal interpreter and similarity-gated source-preference baseline.
- `sandbox/skillshift.py`: shared reset/observe/execute/evaluate/clone contract using temporary
  files and Git repositories, in-memory SQLite, and an in-process mock API.
- `governor/`: factual applicability and shift features, classical harm prediction, calibrated
  risk decisions, and independent sandbox verification.
- `aem/memory.py`: validated AdverseExperienceMemory with naive, severity-only, and
  counterfactual causal/reliability admission and retrieval weighting.
- `evaluation/prototype.py`: immutable paired execution ledger and S0–S8 ablations.
- `evaluation/run_prototype.py`, `reporting.py`, `validate_artifacts.py`: validation-only model
  selection, held-out evaluation, reports, figures, and reward/artifact recomputation.

These finite action environments execute real isolated resources; they do not sandbox arbitrary
code. Ground-truth fields are excluded from policy and predictor views. Only the evaluator and
explicit verifier use target postconditions. Learned nearest-neighbor candidate retrieval,
generative agent reasoning, and external benchmark generalization remain unimplemented.

## Transfer quantity

Delta(task, skill) = reward_with_skill - reward_without_skill

- Delta > epsilon → HELP
- abs(Delta) <= epsilon → NEUTRAL
- Delta < -epsilon → HARM

`configs/base.yaml: transfer_epsilon` is an infrastructure illustration only.
`configs/experiments.yaml: publication_epsilon` remains null. No final publication epsilon has
been chosen. Define reward, severity, and epsilon before the comparative evaluation.

The WITH executor receives a copied skill; WITHOUT receives None. Future evaluators must freeze
task, model, revision, prompt, and environment and compare policies differing only in skill access.
The skeleton cannot enforce equivalence of external LLM calls or arbitrary executor behavior.
