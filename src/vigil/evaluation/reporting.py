"""Figures and reports generated exclusively from recorded experiment artifacts."""

import hashlib
import html
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve, roc_curve

FIGURES = [
    "01_similarity_vs_transfer.png",
    "02_transfer_by_category.png",
    "03_negative_transfer_by_system.png",
    "04_success_by_system.png",
    "05_harm_predictor_roc.png",
    "06_harm_predictor_pr.png",
    "07_calibration.png",
    "08_aem_failure_recurrence.png",
    "09_aem_tradeoff.png",
]


def finite_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): finite_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_json(item) for item in value]
    if isinstance(value, np.generic):
        return finite_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def save_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(finite_json(data), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def number(value: Any) -> str:
    return "NOT AVAILABLE" if value is None or pd.isna(value) else f"{value:.4f}"


def markdown_table(frame: pd.DataFrame) -> str:
    def cell(value: Any) -> str:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "NOT AVAILABLE"
        return number(value) if isinstance(value, (float, np.floating)) else str(value)

    header = "| " + " | ".join(frame.columns) + " |\n"
    separator = "| " + " | ".join("---" for _ in frame.columns) + " |\n"
    rows = "".join(
        "| " + " | ".join(cell(value) for value in row) + " |\n"
        for row in frame.itertuples(index=False, name=None)
    )
    return header + separator + rows


def generate_figures(
    output: Path,
    pairs: pd.DataFrame,
    systems: pd.DataFrame,
    aem: pd.DataFrame,
    predictions: pd.DataFrame,
) -> None:
    directory = output / "figures"
    directory.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 120,
            "savefig.dpi": 300,
        }
    )

    def save(name: str) -> None:
        plt.tight_layout()
        plt.savefig(directory / name, bbox_inches="tight", facecolor="white")
        plt.close()

    categories = ["EXACT", "NEAR", "NEUTRAL", "NEGATIVE", "DECEPTIVE"]
    fig, ax = plt.subplots(figsize=(7.4, 4.7))
    for category in categories:
        group = pairs[pairs.category == category]
        ax.scatter(group.semantic_similarity, group.transfer_gain, label=category, s=22, alpha=0.7)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set(
        xlabel="Pinned goal cosine similarity",
        ylabel="Measured transfer gain",
        title="Deterministic baseline: similarity and transfer",
    )
    ax.legend(fontsize=8, ncol=3)
    save(FIGURES[0])
    fig, ax = plt.subplots(figsize=(7.4, 4.7))
    groups = [
        pairs.loc[pairs.category == category, "transfer_gain"].to_numpy() for category in categories
    ]
    ax.boxplot(groups, tick_labels=categories, showmeans=True)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set(ylabel="Measured transfer gain", title="Transfer by authored context category")
    save(FIGURES[1])
    heldout = systems[systems.population == "held_out_test"]
    for name, column, ylabel in [
        (FIGURES[2], "NTR", "Negative transfer rate"),
        (FIGURES[3], "success", "Task success rate"),
    ]:
        fig, ax = plt.subplots(figsize=(7.4, 4.7))
        ax.bar(heldout.system, heldout[column], color="#287D8E")
        ax.set(ylim=(0, 1.05), ylabel=ylabel, title="Held-out source families: S0–S8")
        save(name)
    test = predictions[predictions.partition == "test"]
    y = (test.label.to_numpy() == "HARM").astype(int)
    risk = test.calibrated_harm_probability.to_numpy()
    fig, ax = plt.subplots(figsize=(6.2, 4.7))
    if len(set(y)) == 2:
        fpr, tpr, _ = roc_curve(y, risk)
        ax.plot(fpr, tpr, color="#287D8E", label="Selected calibrated predictor")
        ax.plot([0, 1], [0, 1], "--", color="gray", label="Chance reference")
        ax.legend(fontsize=9)
    else:
        ax.text(0.1, 0.5, "NOT AVAILABLE: one measured class")
    ax.set(xlabel="False positive rate", ylabel="True positive rate", title="Held-out HARM ROC")
    save(FIGURES[4])
    fig, ax = plt.subplots(figsize=(6.2, 4.7))
    if y.sum():
        precision, recall, _ = precision_recall_curve(y, risk)
        ax.plot(recall, precision, color="#287D8E")
        ax.axhline(y.mean(), linestyle="--", color="gray", label="Measured prevalence")
        ax.legend(fontsize=9)
    else:
        ax.text(0.1, 0.5, "NOT AVAILABLE: no measured HARM")
    ax.set(xlabel="Recall", ylabel="Precision", title="Held-out HARM precision–recall")
    save(FIGURES[5])
    fig, ax = plt.subplots(figsize=(6.2, 4.7))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfect-calibration reference")
    for column, label in [
        ("native_harm_probability", "Native"),
        ("calibrated_harm_probability", "Selected calibration"),
    ]:
        true, predicted = calibration_curve(y, test[column], n_bins=10)
        ax.plot(predicted, true, "o-", label=label)
    ax.legend(fontsize=9)
    ax.set(
        xlabel="Mean predicted HARM probability",
        ylabel="Observed HARM fraction",
        title="Held-out reliability (small clustered sample)",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    save(FIGURES[6])
    fig, ax = plt.subplots(figsize=(6.8, 4.7))
    if not aem.empty:
        ax.bar(aem.system, aem.FRR, color="#287D8E")
    else:
        ax.text(0.1, 0.5, "NOT AVAILABLE: no eligible adverse seeds")
    ax.set(
        ylim=(0, 1.05),
        ylabel="Failure recurrence rate",
        title="Prospective AEM recurrence controls",
    )
    save(FIGURES[7])
    fig, ax = plt.subplots(figsize=(6.8, 4.7))
    if not aem.empty:
        for index, row in enumerate(aem.itertuples()):
            ax.scatter(row.OAR, row.FRR, s=60, marker=["o", "s", "^", "D"][index], label=row.system)
        ax.legend(title="Systems (overlapping points retained)")
    else:
        ax.text(0.1, 0.5, "NOT AVAILABLE: no eligible adverse seeds")
    ax.set(
        xlabel="Over-avoidance rate",
        ylabel="Failure recurrence rate",
        title="AEM recurrence / safe-use tradeoff",
        xlim=(-0.05, 1.05),
        ylim=(-0.05, 1.05),
    )
    save(FIGURES[8])


def generate_reports(
    output: Path,
    summary: dict[str, Any],
    systems: pd.DataFrame,
    aem: pd.DataFrame,
    pairs: pd.DataFrame,
) -> list[dict[str, str]]:
    config = summary["configuration"]
    similarity = summary["similarity"]
    learning = summary["harm_predictor"]
    all_systems = systems[systems.population == "all_descriptive"]
    heldout = systems[systems.population == "held_out_test"]
    baseline = all_systems.set_index("system")
    test_baseline = heldout.set_index("system")
    s1 = baseline.loc["S1"]
    s5 = baseline.loc["S5"]
    test_metrics = learning["held_out_test"]
    claims = [
        {
            "claim": "Procedural memory can cause negative transfer in this deterministic baseline",
            "experiment": "200 identical-state WITH/WITHOUT pairs",
            "metric": "NTR",
            "measured_result": number(float(s1.NTR)),
            "artifact": "paired_results.parquet",
            "limitation": "Fixed source-preference policy and complete action macros; not an "
            "LLM result",
            "status": "SUPPORTED" if s1.NTR > 0 else "UNSUPPORTED",
        },
        {
            "claim": "High goal similarity guarantees nonnegative transfer",
            "experiment": "Pinned cosine versus executed reward difference",
            "metric": "high_similarity_harm_rate",
            "measured_result": number(similarity["high_similarity_harm_rate"]),
            "artifact": "paired_results.parquet",
            "limitation": "One embedding model, selected source candidates, synthetic corpus",
            "status": "UNSUPPORTED"
            if (similarity["high_similarity_harm_rate"] or 0) > 0
            else "INCONCLUSIVE",
        },
        {
            "claim": "Risk-aware governance reduces harmful reuse versus S1 in this baseline",
            "experiment": "S1 versus S5 executed held-out ablation",
            "metric": "Held-out NTR difference S5 minus S1",
            "measured_result": number(
                float(test_baseline.loc["S5", "NTR"] - test_baseline.loc["S1", "NTR"])
            ),
            "artifact": "system_comparison.csv",
            "limitation": "Goal constraints directly reveal applicability; selected predictor "
            "may duplicate a factual gate",
            "status": "SUPPORTED"
            if test_baseline.loc["S5", "NTR"] < test_baseline.loc["S1", "NTR"]
            else "UNSUPPORTED",
        },
        {
            "claim": "The selected predictor discriminates HARM on held-out source skills",
            "experiment": "Validation-only selection then held-out evaluation",
            "metric": "AUROC / AUPRC",
            "measured_result": number(test_metrics["AUROC"])
            + " / "
            + number(test_metrics["AUPRC"]),
            "artifact": "predictions.parquet; summary.json",
            "limitation": "Eight test families; shared synthetic context templates",
            "status": "SUPPORTED"
            if test_metrics["AUROC"] is not None and test_metrics["AUROC"] >= 0.8
            else "INCONCLUSIVE",
        },
        {
            "claim": "Beneficial transfer is retained by governance and AEM",
            "experiment": "Measured HELP opportunities across S0–S8",
            "metric": "PTR",
            "measured_result": number(baseline.loc["S8", "PTR"]),
            "artifact": "system_comparison.csv",
            "limitation": "Undefined if the no-memory macro policy leaves no measured HELP "
            "opportunities",
            "status": "INCONCLUSIVE",
        },
    ]
    if not aem.empty:
        by_system = aem.set_index("system")
        reduction = float(by_system.loc["S5", "FRR"] - by_system.loc["S8", "FRR"])
        claims.extend(
            [
                {
                    "claim": "Full AEM adds recurrence reduction over VIGIL without AEM",
                    "experiment": "Prospective seed/recurrence/safe/unrelated controls",
                    "metric": "FRR S5 minus S8",
                    "measured_result": number(reduction),
                    "artifact": "aem_controls.parquet; aem_comparison.csv",
                    "limitation": "A zero-recurrence floor hides incremental benefit",
                    "status": "SUPPORTED" if reduction > 0 else "UNSUPPORTED",
                },
                {
                    "claim": "Causality/reliability weighting improves over severity-only memory",
                    "experiment": "S7 versus S8 recurrence and safe-use controls",
                    "metric": "FRR / OAR difference",
                    "measured_result": number(
                        float(by_system.loc["S8", "FRR"] - by_system.loc["S7", "FRR"])
                    )
                    + " / "
                    + number(float(by_system.loc["S8", "OAR"] - by_system.loc["S7", "OAR"])),
                    "artifact": "adverse_memory.json; aem_comparison.csv",
                    "limitation": "Deterministic causal scores/confidence can be identically one; "
                    "weights then collapse to severity",
                    "status": "INCONCLUSIVE",
                },
            ]
        )
    traps = (
        pairs[pairs.transfer_gain < -config["epsilon"]]
        .sort_values("semantic_similarity", ascending=False)
        .head(10)
    )
    metric_rows = []
    for name, row in learning["validation_models"].items():
        metric_rows.append(
            {
                "model": name,
                "population": "validation",
                **{
                    key: row.get(key)
                    for key in ["AUROC", "AUPRC", "precision", "recall", "F1", "Brier"]
                },
            }
        )
    metric_rows.append(
        {
            "model": learning["selected_model"] + " + " + learning["selected_calibration"],
            "population": "held_out_test",
            **{
                key: test_metrics[key]
                for key in ["AUROC", "AUPRC", "precision", "recall", "F1", "Brier"]
            },
        }
    )
    limitations = (
        "No real LLM experiment: credentials were unavailable. These are "
        "DETERMINISTIC BASELINE results. "
        "Source preference is an engineering policy, not learned LLM "
        "behavior. Complete Phase 1 action macros "
        "can make no-memory execution sufficient; absent HELP cases leave PTR "
        "and HELP recall undefined. "
        "All-corpus tables include fitting/calibration families and are "
        "descriptive. The held-out set has "
        "eight source families with shared cross-domain templates; this is "
        "not external generalization. "
        "Goal/permission facts are explicit. Deterministic replay makes "
        "attribution confidence a simplified baseline. "
        "AEM controls are seeded prospective repeats, not independent new "
        "benchmark tasks. "
        "Severe seeds use separately identified forced-source intervention pairs, "
        "not naturally occurring failures of the cosine-gated S1 policy. "
        "Similarity correlations are conditional on S1's cosine eligibility gate. "
        "Bootstrap/sign-flip statistics describe synthetic-family variation; "
        "task-level McNemar ignores clustering. "
        "No publication epsilon or publication-level claim is established."
    )
    interpretation = (
        "The paired experiment measures the consequence of exposing source "
        "procedure information to "
        "this fixed policy. Any harmful gain is evidence of negative transfer "
        "for that policy. It does not "
        "establish an LLM retrieval failure. Governance performance should be "
        "compared with the deterministic "
        "precondition gate and no-memory policy, rather than assumed novel. "
        "AEM is valuable only if recurrence "
        "improves without increased avoidance; a floor or collapsed weights "
        "leave its incremental hypothesis unresolved."
    )
    report = (
        "# VIGIL-AEM prototype measured results\n\n**DETERMINISTIC BASELINE — "
        "not LLM results.**\n\n"
    )
    report += (
        "## 1. Experiment configuration\n\n```json\n" + json.dumps(config, indent=2) + "\n```\n\n"
    )
    report += "Real LLM experiment not executed because credentials were unavailable.\n\n"
    report += (
        "## 2. Core baseline and full ablation\n\nAll 200 targets "
        "(descriptive, including training families):\n\n"
    )
    report += markdown_table(
        all_systems[
            [
                "system",
                "tasks",
                "success",
                "mean_transfer_gain",
                "NTR",
                "PTR",
                "verification_frequency",
                "mean_runtime_seconds",
            ]
        ]
    )
    report += "\nFinal held-out families (model/threshold selection already frozen):\n\n"
    report += markdown_table(
        heldout[
            [
                "system",
                "tasks",
                "success",
                "mean_transfer_gain",
                "NTR",
                "PTR",
                "verification_frequency",
            ]
        ]
    )
    report += (
        "\nS0 no memory; S1 cosine-gated source memory; S2 factual "
        "preconditions; S3 native harm predictor; "
    )
    report += (
        "S4 calibrated uncertainty with fallback; S5 sandbox verification; S6 "
        "naive failure memory; "
    )
    report += (
        "S7 severity-only memory; S8 causal/reliability-weighted AEM. Main "
        "AEM uses training memory only.\n\n"
    )
    report += "## 3. Similarity finding\n\n"
    report += markdown_table(
        pd.DataFrame(
            [
                {
                    key: similarity[key]
                    for key in [
                        "Pearson",
                        "Spearman",
                        "mean_transfer_gain",
                        "positive_transfer_rate",
                        "negative_transfer_rate",
                        "high_similarity_harm_rate",
                        "high_similarity_count",
                    ]
                }
            ]
        )
    )
    report += "\n" + markdown_table(pd.DataFrame(similarity["by_category"]))
    report += "\nHighest-cosine measured harmful cases:\n\n" + markdown_table(
        traps[["task_id", "category", "semantic_similarity", "transfer_gain"]]
    )
    report += "\n## 4. Harm predictor and calibration\n\n" + markdown_table(
        pd.DataFrame(metric_rows)
    )
    report += (
        "\nBinary confusion matrix rows=true [non-HARM,HARM], columns=prediction:\n\n```json\n"
    )
    report += json.dumps(test_metrics["confusion_matrix"]) + "\n```\n\n"
    report += (
        "Multiclass order [HELP,NEUTRAL,HARM]; absent-class recall is NOT AVAILABLE.\n\n```json\n"
    )
    report += (
        json.dumps(
            {
                key: test_metrics[key]
                for key in [
                    "multiclass_accuracy",
                    "multiclass_macro_F1_all_three_labels",
                    "multiclass_confusion_matrix",
                    "class_support",
                    "absent_class_metrics",
                ]
            },
            indent=2,
        )
        + "\n```\n\n"
    )
    report += "Validation calibration candidates:\n\n" + markdown_table(
        pd.DataFrame(
            [
                {"method": name, "Brier": row["Brier"], "ECE": row["ECE"]}
                for name, row in learning["validation_calibration"].items()
            ]
        )
    )
    report += (
        "\nSimilarity-only validation ablation:\n\n```json\n"
        + json.dumps(learning["similarity_only_validation"], indent=2)
        + "\n```\n\n"
    )
    report += (
        "## 5. VIGIL comparison\n\nAll S0–S8 measurements appear above. "
        "Runtime includes actual fixture setup/execution; "
    )
    report += (
        "verification runtime is separately logged. An untriggered verifier "
        "adds no measured execution cost.\n\n"
    )
    report += "## 6. AEM recurrence comparison\n\n" + markdown_table(aem)
    report += (
        "\nFRR is measured only for eligible harmful recurrences; CFA uses "
        "severe recurrence cases; "
    )
    report += (
        "OAR counts avoided source use on measured safe controls, even if "
        "fallback still solves the task. "
    )
    report += (
        "PTR is NOT AVAILABLE when its measured HELP denominator is zero. `aem_controls.parquet` "
    )
    report += (
        "identifies exact/related recurrence, similar-safe and unrelated "
        "trials and their seed execution.\n\n"
    )
    report += "## 7. Ablations and claims\n\n" + markdown_table(pd.DataFrame(claims))
    statistics = json.loads((output / "statistics.json").read_text(encoding="utf-8"))
    effect_rows = []
    for experiment, row in statistics.items():
        effect_rows.append(
            {
                "experiment": experiment,
                "families": row["cluster_count"],
                "tasks": row["task_count"],
                "mean_reward_effect": row["mean_reward_effect"],
                "cluster_bootstrap_95_CI": "["
                + ", ".join(number(v) for v in row["bootstrap_95_ci"])
                + "]",
                "cluster_sign_flip_p": row["paired_cluster_permutation_p"],
                "task_McNemar_p": row["mcnemar_exact_p"],
            }
        )
    report += (
        "\nPaired reward effects (exploratory finite-corpus statistics):\n\n"
        + markdown_table(pd.DataFrame(effect_rows))
    )
    report += (
        "\nThese p-values are descriptive analysis aids, not population significance claims. "
        "McNemar ignores within-family dependence; the held-out comparison has eight "
        "synthetic source families.\n\n"
    )
    component_rows = []
    for system, reference in [
        ("S2", "S1"),
        ("S3", "S2"),
        ("S4", "S3"),
        ("S5", "S4"),
        ("S6", "S5"),
        ("S7", "S5"),
        ("S8", "S5"),
    ]:
        component_rows.append(
            {
                "comparison": f"{system} versus {reference} (held-out)",
                "success_difference": test_baseline.loc[system, "success"]
                - test_baseline.loc[reference, "success"],
                "NTR_difference": test_baseline.loc[system, "NTR"]
                - test_baseline.loc[reference, "NTR"],
                "verification_frequency_difference": test_baseline.loc[
                    system, "verification_frequency"
                ]
                - test_baseline.loc[reference, "verification_frequency"],
            }
        )
    report += (
        "Observed component additions (zero outcome differences mean no measured improvement):\n\n"
        + markdown_table(pd.DataFrame(component_rows))
    )
    report += "\n## 8. Scientific interpretation\n\n### OBSERVED\n\n"
    report += (
        "All numeric observations above were calculated from recorded executions and predictions. "
    )
    help_count = int((pairs.label == "HELP").sum())
    report += (
        f"Measured labels: {json.dumps(summary['labels'], sort_keys=True)}. "
        f"HELP count={help_count}. "
    )
    if help_count == 0:
        report += "Its zero denominator leaves PTR unavailable. "
    report += (
        f"{summary['raw_executions']} individual executions are recorded, including "
        f"{summary['forced_control_pairs']} separately identified forced-source control pairs. "
    )
    report += (
        "`statistics.json` supplies paired effects, clustered 95% intervals "
        "and exploratory tests.\n\n"
    )
    report += (
        "### INTERPRETATION\n\n" + interpretation + "\n\n### LIMITATION\n\n" + limitations + "\n\n"
    )
    report += (
        "## Reproduction\n\n```sh\nuv sync --locked\nuv run --locked python "
        "experiments/fast_prototype.py --output results/reproduction\nuv run "
        "--locked python scripts/validate_prototype_results.py --root "
        "results/reproduction\n```\n"
    )
    (output / "FINAL_RESULTS.md").write_text(report, encoding="utf-8")
    aem_findings = (
        "NOT AVAILABLE: no eligible seeded recurrence"
        if aem.empty
        else (
            "Full AEM FRR="
            + number(aem.set_index("system").loc["S8", "FRR"])
            + ", OAR="
            + number(aem.set_index("system").loc["S8", "OAR"])
            + "; VIGIL without AEM FRR="
            + number(aem.set_index("system").loc["S5", "FRR"])
        )
    )
    executive = (
        "Problem: inappropriate reuse of source procedures can harm new tasks.\n"
        f"Experiment: {len(pairs)} synthetic targets, one same-state pair per "
        f"task, a fixed deterministic "
        "policy, pinned CPU goal embeddings, eight held-out source families, "
        "S0–S8 ablations.\n"
        f"Measured no-memory success={number(baseline.loc['S0', 'success'])}; "
        f"similarity memory success={number(s1.success)}; "
        f"NTR={number(s1.NTR)}.\n"
        f"High-similarity harm "
        f"rate={number(similarity['high_similarity_harm_rate'])}; "
        f"Pearson={number(similarity['Pearson'])}; "
        f"Spearman={number(similarity['Spearman'])}.\n"
        f"Selected predictor={learning['selected_model']}; held-out "
        f"AUROC={number(test_metrics['AUROC'])}, "
        f"AUPRC={number(test_metrics['AUPRC'])}; S5 NTR={number(s5.NTR)}.\n"
        f"AEM: {aem_findings}.\n"
        + (
            "High goal similarity was insufficient to guarantee safe reuse in this policy.\n"
            if (similarity["high_similarity_harm_rate"] or 0) > 0
            else "No high-similarity harmful reuse was observed; sufficiency is inconclusive.\n"
        )
        + f"Measured HELP opportunities={help_count}; PTR="
        + number(baseline.loc["S8", "PTR"])
        + ".\n"
        + "These are deterministic baseline results. Real LLM experiment not "
        "executed because credentials were unavailable.\n"
        "No-memory macros may leave no measured HELP opportunities; PTR then "
        "is undefined. Small shared "
        "synthetic templates and seeded repeats do not establish LLM or "
        "real-world generalization. "
        "Incremental AEM benefit is not demonstrated by equal/floor "
        "recurrence rates.\n"
    )
    (output / "EXECUTIVE_SUMMARY.txt").write_text(executive, encoding="utf-8")
    page = (
        "<!doctype html><html lang='en'><meta "
        "charset='utf-8'><title>VIGIL-AEM measured prototype</title>"
    )
    page += (
        "<style>body{font:16px system-ui;max-width:1100px;"
        "margin:40px auto;padding:0 24px;color:#18313b}"
        "table{border-collapse:collapse;font-size:13px}"
        "td,th{padding:8px;border:1px solid #ccc}"
        "img{max-width:100%;display:block}"
        "pre{white-space:pre-wrap;background:#f5f7f8;padding:16px}"
        "h2{margin-top:40px}</style>"
    )
    page += (
        "<h1>VIGIL-AEM measured prototype</h1><p><strong>DETERMINISTIC "
        "BASELINE. No generative LLM experiment.</strong></p>"
    )
    page += (
        "<h2>Research question</h2><p>Can harmful procedural reuse be "
        "predicted and reduced without unnecessarily blocking beneficial "
        "reuse?</p>"
    )
    page += (
        "<h2>Methodology and reproducibility</h2><pre>"
        + html.escape(json.dumps(config, indent=2))
        + "</pre>"
    )
    page += (
        "<p>Paired independent fixtures; source-skill splits; validation-only "
        "selection; deterministic reward. Reports are generated from saved "
        "records.</p>"
    )
    page += "<h2>Held-out S0–S8 outcomes</h2>" + heldout.to_html(
        index=False, na_rep="NOT AVAILABLE"
    )
    page += "<h2>Harm prediction</h2>" + pd.DataFrame(metric_rows).to_html(
        index=False, na_rep="NOT AVAILABLE"
    )
    page += "<h2>Prospective AEM controls</h2>" + aem.to_html(index=False, na_rep="NOT AVAILABLE")
    for filename in FIGURES:
        page += (
            f"<h2>{html.escape(filename)}</h2><img alt='{html.escape(filename)}' "
            f"src='figures/{filename}'>"
        )
    page += "<h2>Conclusions and evidence</h2>" + pd.DataFrame(claims).to_html(index=False)
    page += "<h2>Exploratory paired effects</h2>" + pd.DataFrame(effect_rows).to_html(index=False)
    page += "<h2>Interpretation</h2><p>" + html.escape(interpretation) + "</p>"
    page += "<h2>Limitations</h2><p>" + html.escape(limitations) + "</p>"
    page += "<h2>Executive summary</h2><pre>" + html.escape(executive) + "</pre></html>"
    (output / "report.html").write_text(page, encoding="utf-8")
    return claims


def artifact_manifest(output: Path) -> None:
    hashes = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "artifact_checksums.json":
            hashes[path.relative_to(output).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    save_json(output / "artifact_checksums.json", hashes)
