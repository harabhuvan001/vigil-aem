# Future experiment protocol

No comparative research experiment has been run. These are requirements for later work.

1. State the hypothesis, experiment, primary metric, ablation, and analysis plan for every component.
2. Freeze the LLM weights/API model identifier and revision during a comparative experiment.
   If a hosted provider cannot pin a revision, record that limitation and run conditions together.
3. Use the same prompt/version, decoding parameters, tool definitions, and budgets between
   conditions except the explicitly manipulated skill information. Version prompts in Git.
4. Start WITH_SKILL and WITHOUT_SKILL paired runs from identical environment state. Use independent
   environments; prevent state carryover and reset all mutable fixtures.
5. Fix and log seeds where applicable. Repeat stochastic runs and record the number of repetitions.
   A seed does not guarantee deterministic hosted inference. Randomize condition order as appropriate.
6. Predefine evaluation thresholds, reward, severity weights, epsilon, costs, stopping rules, and
   exclusion criteria. The bootstrap epsilon is illustrative; publication epsilon is unset.
7. Split train/validation/test by task/skill family and retain a split manifest. Prevent near-duplicate
   task templates and procedural variants from crossing held-out family boundaries.
8. Avoid benchmark leakage into retrieval stores, AEM, training, prompts, hyperparameter selection,
   or model choice. Fit preprocessing using training data only.
9. Report sample sizes, paired reward deltas, HELP/NEUTRAL/HARM classification, confidence intervals,
   harm precision/recall and calibration where relevant, and severity-weighted repeated failure rates.
   Define the resampling unit and account for family clustering; do not treat correlated repetitions
   as independent tasks. Statistical routines are not yet implemented.
10. Never alter ground truth after viewing test performance. Freeze and version annotations; legitimate
    corrections require an auditable new dataset version and evaluation disclosure.
11. Keep observed results, expected hypotheses, illustrative examples, and external literature results
    explicitly distinct. Never fabricate results or treat smoke metrics as empirical research findings.
12. Log Git commit, lockfile hash, package versions, OS, Python, model identifier/revision, prompt
    version, seed, task/skill/split IDs, conditions, and artifacts for every future experiment.

Suggested progression: SkillShiftBench v0.1 specification → no-memory vs similarity-memory
baseline → preconditions → harm predictor → verification → AEM. Each transition requires
a concrete hypothesis and isolated ablation, not architectural complexity alone.
