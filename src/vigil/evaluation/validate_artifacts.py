"""Recompute assertions from raw environment records; fail rather than fill missing results."""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image

from vigil.aem.memory import AdverseMemoryEvent
from vigil.benchmark.catalog import STATE_ADAPTER
from vigil.benchmark.dataset import checksum_bytes, load_corpus, verify_checksums
from vigil.evaluation.prototype import Trial, summarize_aem, summarize_systems, transfer_label
from vigil.evaluation.prototype_schema import digest, load_split, public_view
from vigil.evaluation.reporting import FIGURES
from vigil.governor.risk import predictor_metrics
from vigil.sandbox.skillshift import score

REQUIRED = [
    "phase1_validation.txt",
    "FINAL_RESULTS.md",
    "EXECUTIVE_SUMMARY.txt",
    "report.html",
    "raw_runs.parquet",
    "paired_results.parquet",
    "features.parquet",
    "predictions.parquet",
    "system_comparison.csv",
    "aem_comparison.csv",
    "summary.json",
    "statistics.json",
    "environment.json",
    "benchmark_checksum.txt",
    "system_trials.parquet",
    "aem_controls.parquet",
    "fitted_predictor.pkl",
    "feature_schema.json",
    "split_manifest.json",
    "split_manifest.sha256",
    "frozen_selection.json",
    "artifact_checksums.json",
    "all_goal_similarities.parquet",
    "execution_ledger.jsonl",
    "claims.json",
    "forced_control_pairs.parquet",
    "forced_control_features.parquet",
    "control_adverse_memory.json",
]


def equal_metrics(left: pd.Series, right: pd.Series) -> bool:
    """Treat an undefined rate consistently across object-Parquet and numeric-CSV dtypes."""
    return bool(
        np.allclose(
            left.to_numpy(dtype=float, na_value=np.nan),
            right.to_numpy(dtype=float, na_value=np.nan),
            equal_nan=True,
        )
    )


def validate_results(root: Path, repository: Path) -> dict[str, Any]:
    skills, tasks, _ = load_corpus(repository / "benchmark")
    verify_checksums(repository / "benchmark")
    task_map = {task.task_id: task for task in tasks}
    split = load_split(repository / "configs/fast_prototype_splits.json", skills)
    for name in REQUIRED + [f"figures/{name}" for name in FIGURES]:
        if not (root / name).is_file() or (root / name).stat().st_size == 0:
            raise ValueError(f"Missing/empty required artifact: {name}")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    epsilon = summary["configuration"]["epsilon"]
    pairs = pd.read_parquet(root / "paired_results.parquet")
    features = pd.read_parquet(root / "features.parquet")
    predictions = pd.read_parquet(root / "predictions.parquet")
    raw = pd.read_parquet(root / "raw_runs.parquet")
    if len(pairs) != 200 or len(features) != 200 or len(predictions) != 200:
        raise ValueError("Expected 200 pairs, feature rows and predictions")
    if pairs.task_id.nunique() != 200 or raw.execution_id.nunique() != len(raw):
        raise ValueError("Duplicate measured identities")
    if (root / "benchmark_checksum.txt").read_bytes() != checksum_bytes(repository / "benchmark"):
        raise ValueError("Run benchmark checksum mismatch")
    manifest = json.loads((root / "artifact_checksums.json").read_text(encoding="utf-8"))
    for path, expected in manifest.items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Result artifact hash changed: {path}")
    for filename in FIGURES:
        with Image.open(root / "figures" / filename) as image:
            if image.width < 500 or image.height < 400 or image.format != "PNG":
                raise ValueError("Figure resolution/format is invalid")
            image.verify()
    rows = {record.execution_id: record for record in raw.itertuples()}
    ledger = [
        Trial.model_validate_json(line)
        for line in (root / "execution_ledger.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if {trial.execution_id for trial in ledger} != set(rows):
        raise ValueError("Raw runs differ from execution ledger identities")
    for name in ("adverse_memory.json", "control_adverse_memory.json"):
        for saved_event in json.loads((root / name).read_text(encoding="utf-8")):
            event = AdverseMemoryEvent.model_validate(saved_event)
            without, with_skill, replay = [rows[key] for key in event.source_execution_ids]
            causal = max(0.0, min(1.0, (without.reward - with_skill.reward) / 2))
            if event.causal_score != causal or event.severity != with_skill.severity:
                raise ValueError("AEM severity/causality not derived from execution")
            if event.diagnosis_confidence == 1 and (
                with_skill.final_state_hash != replay.final_state_hash
                or without.initial_state_hash != with_skill.initial_state_hash
            ):
                raise ValueError("AEM attribution replay mismatch")
    for record in raw.to_dict(orient="records"):
        trial = Trial.model_validate(record)
        task = task_map[trial.task_id]
        final = STATE_ADAPTER.validate_json(trial.final_state_json)
        measured = score(task, trial.action, final)
        if (
            measured.reward != trial.reward
            or measured.success != trial.success
            or measured.severity != trial.severity
        ):
            raise ValueError("Raw reward disagrees with saved environment-derived final state")
        if trial.initial_state_hash != digest(
            task.initial_state
        ) or trial.final_state_hash != digest(final):
            raise ValueError("Raw state hash mismatch")
        if trial.public_view_hash != digest(public_view(task, task.initial_state)):
            raise ValueError("Raw agent view mismatch")
    for pair in pairs.itertuples():
        without = rows[pair.execution_without]
        with_skill = rows[pair.execution_with]
        if (
            without.initial_state_hash != with_skill.initial_state_hash
            or without.public_view_hash != with_skill.public_view_hash
        ):
            raise ValueError("Counterfactual initial-state/view hashes differ")
        if without.skill_exposed or not with_skill.skill_exposed:
            raise ValueError("Paired exposure condition invalid")
        if pair.transfer_gain != with_skill.reward - without.reward:
            raise ValueError("Paired gain not derived from raw runs")
        if pair.label != transfer_label(pair.transfer_gain, epsilon):
            raise ValueError("Transfer label mismatch")
        if pair.partition != split.partition(pair.source_skill_id):
            raise ValueError("Family split leakage")
    if not np.isfinite(
        features[["semantic_similarity", "applicability_score", "shift_score"]].to_numpy()
    ).all():
        raise ValueError("Nonfinite experiment features")
    if features.set_index("task_id").label.to_dict() != pairs.set_index("task_id").label.to_dict():
        raise ValueError("Feature labels not linked to measured gains")
    with (root / "fitted_predictor.pkl").open("rb") as stream:
        fitted = pickle.load(stream)  # Local artifact produced by this trusted run only.
    test_features = features[features.partition == "test"]
    recomputed_metrics = predictor_metrics(test_features.label, fitted.probabilities(test_features))
    for metric in ["AUROC", "AUPRC", "precision", "recall", "F1", "Brier"]:
        expected = recomputed_metrics[metric]
        saved = summary["harm_predictor"]["held_out_test"][metric]
        if expected is None and saved is None:
            continue
        if expected is None or saved is None or not np.isclose(expected, saved):
            raise ValueError(f"Predictor metric differs from fitted model: {metric}")
    forced_pairs = pd.read_parquet(root / "forced_control_pairs.parquet")
    forced_features = pd.read_parquet(root / "forced_control_features.parquet")
    for pair in forced_pairs.itertuples():
        without, with_skill = rows[pair.execution_without], rows[pair.execution_with]
        if without.initial_state_hash != with_skill.initial_state_hash:
            raise ValueError("Forced control state mismatch")
        if pair.transfer_gain != with_skill.reward - without.reward:
            raise ValueError("Forced control gain mismatch")
        if pair.label != transfer_label(pair.transfer_gain, epsilon):
            raise ValueError("Forced control label mismatch")
    if (
        forced_features.set_index("task_id").label.to_dict()
        != forced_pairs.set_index("task_id").label.to_dict()
    ):
        raise ValueError("Forced control feature labels differ from measurements")
    all_cosines = pd.read_parquet(root / "all_goal_similarities.parquet")
    if len(all_cosines) != 200 * 40:
        raise ValueError("Expected all 8000 goal cosine pairs")
    systems = pd.read_parquet(root / "system_trials.parquet")
    if len(systems) != 200 * 9 or set(systems.system) != {f"S{i}" for i in range(9)}:
        raise ValueError("Incomplete S0-S8 execution")
    expected_systems = summarize_systems(systems, pairs, features, epsilon)
    saved_systems = pd.read_csv(root / "system_comparison.csv")
    for column in ["success", "mean_transfer_gain", "NTR", "PTR", "verification_frequency"]:
        if not equal_metrics(expected_systems[column], saved_systems[column]):
            raise ValueError("System table is not derived from trials")
    controls = pd.read_parquet(root / "aem_controls.parquet")
    for frame in (systems, controls):
        for record in frame.itertuples():
            measured_trial = rows[record.execution_id]
            if (record.reward, record.success, record.action) != (
                measured_trial.reward,
                measured_trial.success,
                measured_trial.action,
            ):
                raise ValueError("System/control result differs from its raw execution")
    if not controls.empty:
        if set(controls.control) != {
            "exact_recurrence",
            "related_recurrence",
            "similar_safe",
            "unrelated",
        }:
            raise ValueError("Incomplete AEM controls")
        expected_aem = summarize_aem(controls, epsilon)
        saved_aem = pd.read_csv(root / "aem_comparison.csv")
        for column in ["FRR", "CFA", "OAR", "PTR", "NTR", "success"]:
            if not equal_metrics(expected_aem[column], saved_aem[column]):
                raise ValueError("AEM table is not derived from trials")
    page = (root / "report.html").read_text(encoding="utf-8")
    if (
        "http://" in page
        or "https://" in page
        or any(f"figures/{name}" not in page for name in FIGURES)
    ):
        raise ValueError("HTML report must be local and include every figure")
    if summary["configuration"]["target_tasks"] != len(pairs):
        raise ValueError("Reported task count differs from actual pairs")
    return {
        "status": "PASS",
        "pairs": len(pairs),
        "raw_executions": len(raw),
        "systems": 9,
        "figures": len(FIGURES),
        "checksum": "PASS",
        "rewards_recomputed": len(raw),
        "leakage_checks": "PASS",
        "reports": "PASS",
        "validation_scope": "actual saved artifacts",
    }
