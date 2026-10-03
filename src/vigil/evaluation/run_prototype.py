"""Single reproducible entry point: measured execution -> models -> ablations -> artifacts."""

import hashlib
import json
import os
import pickle
import shutil
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from scipy.stats import pearsonr, spearmanr

from vigil.benchmark.dataset import checksum_bytes, load_corpus, verify_checksums
from vigil.evaluation.prototype import (
    Recorder,
    compare_systems,
    measure_pairs,
    select_thresholds,
    summarize_aem,
    summarize_systems,
)
from vigil.evaluation.prototype_schema import PrototypeConfig, load_split
from vigil.evaluation.reporting import (
    artifact_manifest,
    finite_json,
    generate_figures,
    generate_reports,
    number,
    save_json,
)
from vigil.evaluation.statistics import paired_statistics
from vigil.governor.risk import CLASSES, FEATURES, predictor_metrics, train_predictors
from vigil.skills.embeddings import goal_similarities
from vigil.utils.version import capture_versions


def source_digest(root: Path) -> str:
    paths = [
        *sorted((root / "src").rglob("*.py")),
        root / "experiments/fast_prototype.py",
        root / "configs/fast_prototype.json",
        root / "configs/fast_prototype_splits.json",
        root / "prompts/deterministic_policy_v1.txt",
        root / "uv.lock",
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def similarity_analysis(pairs: pd.DataFrame, threshold: float) -> dict[str, Any]:
    varied = pairs.transfer_gain.nunique() > 1 and pairs.semantic_similarity.nunique() > 1
    high = pairs.semantic_similarity >= threshold
    by_category = []
    for category, group in pairs.groupby("category", sort=False):
        by_category.append(
            {
                "category": category,
                "tasks": len(group),
                "mean_transfer_gain": float(group.transfer_gain.mean()),
                "positive_transfer_rate": float((group.label == "HELP").mean()),
                "negative_transfer_rate": float((group.label == "HARM").mean()),
            }
        )
    return {
        "Pearson": float(pearsonr(pairs.semantic_similarity, pairs.transfer_gain).statistic)
        if varied
        else None,
        "Spearman": float(spearmanr(pairs.semantic_similarity, pairs.transfer_gain).statistic)
        if varied
        else None,
        "mean_transfer_gain": float(pairs.transfer_gain.mean()),
        "positive_transfer_rate": float((pairs.label == "HELP").mean()),
        "negative_transfer_rate": float((pairs.label == "HARM").mean()),
        "high_similarity_count": int(high.sum()),
        "high_similarity_harm_rate": float((pairs.loc[high, "label"] == "HARM").mean())
        if high.any()
        else None,
        "by_category": by_category,
        "correlation_inference": "Descriptive only; five correlated variants per source skill",
    }


def print_summary(summary: dict[str, Any], systems: pd.DataFrame, aem: pd.DataFrame) -> None:
    indexed = systems[systems.population == "all_descriptive"].set_index("system")
    predictor = summary["harm_predictor"]
    print("\nVIGIL-AEM PROTOTYPE RESULTS", flush=True)
    fields = {
        "Benchmark": summary["configuration"]["benchmark_version"],
        "Tasks": summary["configuration"]["target_tasks"],
        "Pairs evaluated": summary["configuration"]["paired_executions"],
        "Agent/model": "DETERMINISTIC BASELINE",
        "No-memory success": number(indexed.loc["S0", "success"]),
        "Similarity-memory success": number(indexed.loc["S1", "success"]),
        "Negative transfer rate": number(indexed.loc["S1", "NTR"]),
        "High-similarity harm rate": number(summary["similarity"]["high_similarity_harm_rate"]),
        "Best harm predictor": predictor["selected_model"],
        "AUROC": number(predictor["held_out_test"]["AUROC"]),
        "AUPRC": number(predictor["held_out_test"]["AUPRC"]),
        "VIGIL NTR": number(indexed.loc["S5", "NTR"]),
        "Full AEM NTR": number(indexed.loc["S8", "NTR"]),
        "Failure recurrence": number(aem.set_index("system").loc["S8", "FRR"])
        if not aem.empty
        else "NOT AVAILABLE",
        "Over-avoidance": number(aem.set_index("system").loc["S8", "OAR"])
        if not aem.empty
        else "NOT AVAILABLE",
    }
    for name, value in fields.items():
        print(f"{name}: {value}", flush=True)


def write_evidence_docs(root: Path, output: Path, claims: list[dict[str, str]]) -> None:
    from vigil.evaluation.reporting import markdown_table

    text = (
        "# Claims and executable evidence\n\nAll measured values below come "
        "from the deterministic run; no LLM claims are supported.\n\n"
    )
    text += markdown_table(pd.DataFrame(claims))
    text += (
        "\nArtifact root: `"
        + str(output)
        + "`. The complete report distinguishes observations, interpretation "
        "and limitations.\n"
    )
    (root / "docs/CLAIMS_AND_EVIDENCE.md").write_text(text, encoding="utf-8")


def run_experiment(
    root: Path, output: Path, *, resume: bool = False, report_only: bool = False
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    if report_only:
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        pairs = pd.read_parquet(output / "paired_results.parquet")
        systems = pd.read_csv(output / "system_comparison.csv")
        aem = pd.read_csv(output / "aem_comparison.csv")
        predictions = pd.read_parquet(output / "predictions.parquet")
        generate_figures(output, pairs, systems, aem, predictions)
        claims = generate_reports(output, summary, systems, aem, pairs)
        save_json(output / "claims.json", claims)
        write_evidence_docs(root, output, claims)
        artifact_manifest(output)
        print_summary(summary, systems, aem)
        return
    config = PrototypeConfig.model_validate_json((root / "configs/fast_prototype.json").read_text())
    skills, tasks, fixtures = load_corpus(root / "benchmark")
    verify_checksums(root / "benchmark")
    split = load_split(root / "configs/fast_prototype_splits.json", skills)
    np.random.seed(config.seed)
    torch.manual_seed(config.seed)
    torch.set_num_threads(2)
    benchmark = checksum_bytes(root / "benchmark")
    benchmark_hash = hashlib.sha256(benchmark).hexdigest()
    (output / "benchmark_checksum.txt").write_bytes(benchmark)
    phase1 = (
        f"skills={len(skills)} targets={len(tasks)} "
        f"domains={len(set(t.domain for t in tasks))} "
        f"reset_fixtures={len(fixtures)}\n"
        f"skills_by_domain={dict(Counter(s.domain.value for s in skills))}\n"
        f"targets_by_domain={dict(Counter(t.domain.value for t in tasks))}\n"
        "unique_ids=PASS valid_references=PASS five_categories_per_skill=PASS\n"
        "structural_integrity=PASS sha256=PASS\n"
        "deterministic_outcomes=verified_by_fixture_tests_and_actual_trial_evaluation\n"
    )
    (output / "phase1_validation.txt").write_text(phase1, encoding="utf-8")
    provenance = capture_versions(repo_root=root).model_dump()
    started = datetime.now(UTC).isoformat()
    revision = source_digest(root)
    credential_present = any(
        bool(os.environ.get(key))
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY"]
    )
    if credential_present:
        raise ValueError(
            "Provider configuration changed: this frozen deterministic run must "
            "be reviewed before any LLM run"
        )
    git_commit = provenance["git_commit"] or "uncommitted"
    environment = {
        **provenance,
        "source_sha256": revision,
        "lockfile_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(
            (root / "configs/fast_prototype.json").read_bytes()
        ).hexdigest(),
        "split_sha256": hashlib.sha256(
            (root / "configs/fast_prototype_splits.json").read_bytes()
        ).hexdigest(),
        "embedding_model": config.embedding_model,
        "embedding_revision": config.embedding_revision,
        "real_llm_executed": False,
        "real_llm_reason": "credentials were unavailable",
        "provider": None,
        "generative_model": None,
        "model_revision": None,
        "temperature": None,
        "max_tokens": None,
        "maximum_tool_steps": config.max_tool_steps,
        "system_prompt": (root / "prompts/deterministic_policy_v1.txt").read_text(encoding="utf-8"),
        "prompt_version": config.prompt_version,
        "run_timestamp": started,
        "seed": config.seed,
        "resource_policy": "owned temporary filesystem/Git; in-memory SQLite; in-process API; no "
        "arbitrary actions",
        "git_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip()
        ),
    }
    if resume and (output / "environment.json").exists():
        previous = json.loads((output / "environment.json").read_text(encoding="utf-8"))
        if previous["source_sha256"] != revision:
            raise ValueError("Resume requires the same complete source/config fingerprint")
        environment = previous
    save_json(output / "environment.json", environment)
    shutil.copyfile(root / "configs/fast_prototype_splits.json", output / "split_manifest.json")
    shutil.copyfile(root / "configs/fast_prototype_splits.sha256", output / "split_manifest.sha256")
    recorder = Recorder(output, fixtures, config, benchmark_hash, git_commit, resume)
    print("Loading pinned CPU Sentence Transformers; no generative LLM", flush=True)
    similarities, goal_cosines = goal_similarities(tasks, skills, config)
    all_similarity = pd.DataFrame(
        [
            {
                "task_id": task.task_id,
                "skill_id": skill.skill_id,
                "semantic_similarity": float(similarities[i, j]),
            }
            for i, task in enumerate(tasks)
            for j, skill in enumerate(skills)
        ]
    )
    all_similarity.to_parquet(output / "all_goal_similarities.parquet", index=False)
    pairs, features = measure_pairs(tasks, skills, similarities, recorder)
    features["partition"] = features.source_skill_id.map(split.partition)
    pairs["partition"] = pairs.source_skill_id.map(split.partition)
    pairs.to_parquet(output / "paired_results.parquet", index=False)
    features.to_parquet(output / "features.parquet", index=False)
    native, calibrated, learning = train_predictors(features, config.seed)
    validation = pairs[pairs.partition == "validation"]
    validation_features = features[features.partition == "validation"]
    thresholds = select_thresholds(
        validation, calibrated.probabilities(validation_features)[:, 2], config
    )
    save_json(output / "frozen_selection.json", {**learning, "thresholds": thresholds})
    print(
        f"Frozen validation selection: {learning['selected_model']} / "
        f"{learning['selected_calibration']}; thresholds {thresholds['low']}, "
        f"{thresholds['high']}",
        flush=True,
    )
    # First held-out model evaluation occurs only after all selection decisions are serialized.
    test = features[features.partition == "test"]
    learning["held_out_test"] = predictor_metrics(test.label, calibrated.probabilities(test))
    predictions = features[["task_id", "source_skill_id", "partition", "label"]].copy()
    native_probs = native.probabilities(features)
    calibrated_probs = calibrated.probabilities(features)
    predictions["native_harm_probability"] = native_probs[:, 2]
    predictions["calibrated_harm_probability"] = calibrated_probs[:, 2]
    for index, label in enumerate(CLASSES):
        predictions[f"probability_{label}"] = calibrated_probs[:, index]
    predictions.to_parquet(output / "predictions.parquet", index=False)
    with (output / "fitted_predictor.pkl").open("wb") as stream:
        pickle.dump(calibrated, stream)
    save_json(
        output / "feature_schema.json",
        {
            "features": FEATURES,
            "classes": CLASSES,
            "oracle_fields_excluded": True,
            "history_provenance": "source demonstration executions only",
            "constant_features": [name for name in FEATURES if features[name].nunique() <= 1],
        },
    )
    outcomes, controls = compare_systems(
        tasks, skills, pairs, features, native, calibrated, thresholds, recorder, goal_cosines
    )
    outcomes.to_parquet(output / "system_trials.parquet", index=False)
    controls.to_parquet(output / "aem_controls.parquet", index=False)
    systems = summarize_systems(outcomes, pairs, features, config.epsilon)
    aem = summarize_aem(controls, config.epsilon)
    systems.to_csv(output / "system_comparison.csv", index=False)
    aem.to_csv(output / "aem_comparison.csv", index=False)
    raw = pd.DataFrame([trial.model_dump() for trial in recorder.trials.values()])
    raw.to_parquet(output / "raw_runs.parquet", index=False)
    statistics = {
        "core_pairs_all_descriptive": paired_statistics(
            pairs.assign(reward_difference=pairs.transfer_gain),
            seed=config.seed,
            bootstrap=config.bootstrap_repetitions,
            permutations=config.permutation_repetitions,
        )
    }
    heldout_pairs = pairs[pairs.partition == "test"]
    statistics["core_pairs_held_out"] = paired_statistics(
        heldout_pairs.assign(reward_difference=heldout_pairs.transfer_gain),
        seed=config.seed,
        bootstrap=config.bootstrap_repetitions,
        permutations=config.permutation_repetitions,
    )
    test_outcomes = outcomes[outcomes.task_id.isin(heldout_pairs.task_id)]
    s1 = test_outcomes[test_outcomes.system == "S1"].set_index("task_id")
    for system in ["S2", "S3", "S4", "S5", "S6", "S7", "S8"]:
        other = test_outcomes[test_outcomes.system == system].set_index("task_id").loc[s1.index]
        frame = pd.DataFrame(
            {
                "source_skill_id": s1.source_skill_id,
                "reward_difference": other.reward - s1.reward,
                "success_without": s1.success,
                "success_with": other.success,
            }
        )
        statistics[f"{system}_vs_S1_held_out"] = paired_statistics(
            frame,
            seed=config.seed,
            bootstrap=config.bootstrap_repetitions,
            permutations=config.permutation_repetitions,
        )
    save_json(output / "statistics.json", statistics)
    summary = finite_json(
        {
            "configuration": {
                **config.model_dump(),
                "benchmark_version": "SkillShiftBench-v0.1",
                "target_tasks": len(tasks),
                "paired_executions": len(pairs),
                "core_individual_executions": len(pairs) * 2,
                "agent": "DETERMINISTIC BASELINE",
                "git_commit": environment["git_commit"],
                "source_sha256": environment["source_sha256"],
                "run_timestamp": environment["run_timestamp"],
                "real_llm_executed": False,
                "thresholds": thresholds,
                "training_skills": 24,
                "validation_skills": 8,
                "test_skills": 8,
            },
            "similarity": similarity_analysis(pairs, config.similarity_threshold),
            "harm_predictor": learning,
            "system_comparison": systems.to_dict(orient="records"),
            "aem_comparison": aem.to_dict(orient="records"),
            "labels": pairs.label.value_counts().to_dict(),
            "raw_executions": len(raw),
            "forced_control_pairs": int((raw.stage == "forced-control-pair").sum() // 2),
            "aem_eligible_seed_families": controls.seed_task_id.nunique()
            if not controls.empty
            else 0,
            "mean_prior_success_rate": float(features.historical_skill_success_rate.mean()),
        }
    )
    save_json(output / "summary.json", summary)
    generate_figures(output, pairs, systems, aem, predictions)
    claims = generate_reports(output, summary, systems, aem, pairs)
    save_json(output / "claims.json", claims)
    write_evidence_docs(root, output, claims)
    artifact_manifest(output)
    print_summary(summary, systems, aem)
