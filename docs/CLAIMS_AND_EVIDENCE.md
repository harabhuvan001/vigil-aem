# Claims and executable evidence

All measured values below come from the deterministic run; no LLM claims are supported.

| claim | experiment | metric | measured_result | artifact | limitation | status |
| --- | --- | --- | --- | --- | --- | --- |
| Procedural memory can cause negative transfer in this deterministic baseline | 200 identical-state WITH/WITHOUT pairs | NTR | 0.2450 | paired_results.parquet | Fixed source-preference policy and complete action macros; not an LLM result | SUPPORTED |
| High goal similarity guarantees nonnegative transfer | Pinned cosine versus executed reward difference | high_similarity_harm_rate | 0.4667 | paired_results.parquet | One embedding model, selected source candidates, synthetic corpus | UNSUPPORTED |
| Risk-aware governance reduces harmful reuse versus S1 in this baseline | S1 versus S5 executed held-out ablation | Held-out NTR difference S5 minus S1 | -0.3500 | system_comparison.csv | Goal constraints directly reveal applicability; selected predictor may duplicate a factual gate | SUPPORTED |
| The selected predictor discriminates HARM on held-out source skills | Validation-only selection then held-out evaluation | AUROC / AUPRC | 1.0000 / 1.0000 | predictions.parquet; summary.json | Eight test families; shared synthetic context templates | SUPPORTED |
| Beneficial transfer is retained by governance and AEM | Measured HELP opportunities across S0–S8 | PTR | NOT AVAILABLE | system_comparison.csv | Undefined if the no-memory macro policy leaves no measured HELP opportunities | INCONCLUSIVE |
| Full AEM adds recurrence reduction over VIGIL without AEM | Prospective seed/recurrence/safe/unrelated controls | FRR S5 minus S8 | 0.0000 | aem_controls.parquet; aem_comparison.csv | A zero-recurrence floor hides incremental benefit | UNSUPPORTED |
| Causality/reliability weighting improves over severity-only memory | S7 versus S8 recurrence and safe-use controls | FRR / OAR difference | 0.0000 / 0.0000 | adverse_memory.json; aem_comparison.csv | Deterministic causal scores/confidence can be identically one; weights then collapse to severity | INCONCLUSIVE |

Artifact root: `D:\PAPER 1\vigil-aem\results\final_prototype`. The complete report distinguishes observations, interpretation and limitations.
