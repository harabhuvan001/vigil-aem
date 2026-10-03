# Architecture

Status: **environment/bootstrap phase**. The research flow below is planned, not experimentally
validated. Schemas and deterministic infrastructure checks exist; no autonomous agent, trained
harm predictor, learned retrieval, or memory update rule exists yet.

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

Other requested modules are marked **planned**. Experiment entry points 01–06 exit with a
planned-experiment message rather than returning invented research results.

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
