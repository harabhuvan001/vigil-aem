# Fast prototype analysis plan (before measured runs)

This is an exploratory deterministic benchmark experiment, not a preregistered publication or
an LLM evaluation. Phase 1 ground truth and its checksums remain frozen. Publication epsilon in
`configs/experiments.yaml` remains unset. Experimental epsilon is 0.1 on the existing {-1,+1}
reward scale. No reward or severity is relabeled to obtain desired results.

## Hypothesis / experiment / metric / ablation mapping

| Component | Expected hypothesis | Experiment | Metric | Ablation |
|---|---|---|---|---|
| Procedural memory | Similarity alone may admit harmful reuse | Same agent with/without supplied source skill, all 200 tasks | Paired reward delta, NTR, similarity correlations | S0 vs S1 |
| Factual applicability | Inspectable constraints can reject inappropriate reuse | Check source binding, state, permissions, intent | Success, NTR, retained safe reuse | S1 vs S2 |
| Interpretable shift | Context changes provide harm signal | Compare source/target factual context | Held-out HARM AUROC/AUPRC | Predictor feature importances; similarity-only predictor |
| Simple harm prediction | Measured transfer can be predicted within this corpus | Majority, logistic regression, random forest, XGBoost | Binary and multiclass metrics | S2 vs S3 |
| Calibration and uncertainty | Calibrated risk supports cautious decisions | Native, sigmoid, isotonic calibration | Brier, ECE, reliability, task reward | S3 vs S4 |
| Sandbox verification | Executable verification can resolve uncertainty | Independent clone of uncertain candidate execution | NTR, success, verification frequency, elapsed time | S4 vs S5 |
| Adverse Experience Memory | Counterfactual weighting may reduce recurrence with less avoidance | Prospective seeded recurrence and safe/unrelated controls | FRR, CFA, OAR, PTR | S5 vs S6 vs S7 vs S8 |
| Clustered statistics | Pairing and family clustering avoid row pseudo-replication | Skill-cluster bootstrap/sign flips and discordant success tests | Reward effect/95% interval; descriptive tests | Row counts contrasted with independent skill counts |

## Fixed policy and access boundary

The deterministic agent uses one function in both paired conditions. With no skill it reads the
literal task goal: completed-state requests select noop; explicit secondary requests select
apply_secondary; primary requests select apply_primary. Unrecognized goals fail closed to noop.
With an exposed source skill whose goal cosine is at least 0.80, it preferentially uses the
source's primary procedure. This deliberately ungated procedural-memory policy is the S1
engineering baseline. S2 tests whether the source's preconditions should have been checked.
The same view, seed, tools and step budget are used in both conditions. The candidate is the
benchmark-linked source skill, not an oracle-selected nearest skill. Embedding similarities for
all 200 x 40 goal pairs are also archived. Full retrieval generalization is outside this design.

Agent/feature views exclude accepted actions, expected target outcome, category, target metadata,
severity and fixture ID. Facts about protected scopes are parsed from authoritative task text.
The learned skill may expose its own source demonstration state; target oracle fields are only
available to the evaluator and sandbox verifier. No agent can request arbitrary tools.

This baseline may solve all no-memory tasks because Phase 1 exposes complete macros. If no HELP
cases occur, PTR and HELP-class recall are undefined and must be reported NOT AVAILABLE. Do not
weaken the baseline after examining results to manufacture beneficial transfer.

## Freeze and model selection

Use CPU Sentence Transformers `sentence-transformers/all-MiniLM-L6-v2`, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, goal-only text and normalized cosine. This is a real
embedding transformer, not a generative LLM experiment. No supported provider credentials were
found during secure presence-only inspection. No generative LLM call will be attempted.

Seed 42 groups by source skill, stratified by domain: 24 training skills, 8 validation skills,
8 held-out test skills. All five variants stay together. Training is further divided into
12 fitting and 12 calibration skills. Record the split before execution; fit preprocessing only
on fitting data. Related cross-domain templates remain a generalization limitation.

Fixed learners: most-frequent majority, scaled logistic regression (C=1), random forest
(100 trees, depth 4), XGBoost (100 trees, depth 3, learning rate .05, one CPU worker).
Choose on validation AUPRC, then AUROC, then Brier. Compare native/sigmoid/isotonic calibration
using calibration-training families only, select on validation Brier then ECE. Choose low/high
risk thresholds on validation from {.1,.25,.4} x {.6,.75,.9}; objective is measured reward minus
0.1 per verification and 0.1 per avoided safe candidate. Freeze selection before evaluating the
test set once. Absent classes and constant inputs produce null metrics, never invented values.

Historical features come only from separately executed source demonstrations, not target labels.
Main S0-S8 tables separate all-corpus descriptive outcomes from held-out outcomes. Predictor
in-sample performance is never described as generalization evidence.

## AEM and controls

Records include execution IDs and immutable provenance. Full admission requires measured HARM,
a failed WITH outcome and equal initial hashes. Causality is positive reward disadvantage divided
by the reward span (clipped to [0,1]); diagnosis confidence is 1 only when deterministic replay
and pair identity are verified. Priority = severity x causality x diagnosis confidence. Naive
memory admits every failed WITH execution with weight 1; severity-only uses severity.

Retrieval averages equality of factual operation/domain/protection/binding/completion context
and same pinned goal-embedding cosine. A memory raises risk; it never deletes a skill.
Main S6-S8 use training memory only and do not update from held-out outcomes. Separate prospective
controls execute a separate, explicitly forced-candidate WITH/WITHOUT intervention on reserved
primary tasks in held-out families (independent of the similarity eligibility threshold), then
execute exact recurrence,
related recurrence, a same-skill safe EXACT task, and an unrelated other-domain safe EXACT task.
Seed/test controls are explicitly identified and never used for predictor fitting or thresholds.
Their policy differs from the main cosine-gated baseline and must never be pooled into its 200
core pairs. The related reserved-primary case also gets its own directly executed pair to confirm
that it is actually an adverse reuse opportunity. These interventions ensure the requested severe
recurrence controls exist even when retrieval would already exclude them; this is not evidence
that such failures naturally occur under S1 or S5.
A seed with no measured harm is ineligible; preserve and report that exclusion.

FRR = failed recurrence trials / eligible recurrence trials; CFA = avoided failures / eligible
severe recurrence trials; OAR = avoided candidate use / safe controls whose source execution
actually succeeds; PTR = beneficial gains retained / measured HELP opportunities. NTR always
uses reward disadvantage relative to the paired no-memory execution, not merely task failure.
If S5 already avoids every recurrence, additional AEM benefit is unidentifiable at that floor.
If causality/confidence are always 1, full and severity-only weighting cannot be distinguished.

Bootstrap 2000 resamples by source-skill clusters, sign-flip permutation 10000 draws, exact
McNemar on discordant successes with a clustering caveat. Deterministic finite-corpus intervals
describe variation across sampled synthetic families, not stochastic model uncertainty or
population-level proof. Report all negative and null component findings.

Reference implementation guidance: [Sentence Transformers](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html),
[embedding model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), and
[scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html).
