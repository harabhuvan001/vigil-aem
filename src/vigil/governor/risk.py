"""Simple predictors fitted on measured transfer; no benchmark categories as features."""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

FEATURES = [
    "semantic_similarity",
    "applicability_score",
    "failed_precondition_count",
    "shift_score",
    "domain_match",
    "historical_skill_success_rate",
    "historical_skill_failure_rate",
    "previous_usage_count",
]
CLASSES = ["HELP", "NEUTRAL", "HARM"]


def calibration_error(y: Any, probabilities: Any, bins: int = 10) -> float:
    labels = np.asarray(y, dtype=float)
    values = np.asarray(probabilities, dtype=float)
    assignments = np.minimum((values * bins).astype(int), bins - 1)
    error = 0.0
    for index in range(bins):
        mask = assignments == index
        if mask.any():
            error += float(mask.mean() * abs(labels[mask].mean() - values[mask].mean()))
    return error


def predictor_metrics(labels: Any, probabilities: Any) -> dict[str, Any]:
    names = np.asarray(labels)
    values = np.asarray(probabilities)
    harm = (names == "HARM").astype(int)
    risk = values[:, 2]
    predicted_harm = risk >= 0.5
    precision, recall, f1, _ = precision_recall_fscore_support(
        harm, predicted_harm, average="binary", zero_division=0
    )
    multiclass = np.asarray(CLASSES)[values.argmax(axis=1)]
    macro = precision_recall_fscore_support(
        names, multiclass, labels=CLASSES, average="macro", zero_division=0
    )
    two_classes = len(set(harm)) == 2
    return {
        "AUROC": float(roc_auc_score(harm, risk)) if two_classes else None,
        "AUPRC": float(average_precision_score(harm, risk)) if harm.sum() else None,
        "precision": float(precision),
        "recall": float(recall) if harm.sum() else None,
        "F1": float(f1),
        "Brier": float(brier_score_loss(harm, risk)),
        "ECE": calibration_error(harm, risk),
        "confusion_matrix": confusion_matrix(harm, predicted_harm, labels=[0, 1]).tolist(),
        "multiclass_accuracy": float(accuracy_score(names, multiclass)),
        "multiclass_macro_F1_all_three_labels": float(macro[2]),
        "multiclass_confusion_matrix": confusion_matrix(names, multiclass, labels=CLASSES).tolist(),
        "class_support": {name: int((names == name).sum()) for name in CLASSES},
        "absent_class_metrics": [name for name in CLASSES if not (names == name).any()],
    }


@dataclass
class Predictor:
    estimator: Any
    observed_classes: list[str]
    calibration: str = "native"
    calibrator: Any = None

    def probabilities(self, frame: pd.DataFrame) -> Any:
        raw = self.estimator.predict_proba(frame[FEATURES].to_numpy(dtype=float))
        full: Any = np.zeros((len(frame), 3), dtype=float)
        for index, name in enumerate(self.observed_classes):
            full[:, CLASSES.index(name)] = raw[:, index]
        if self.calibration != "native":
            original = np.clip(full[:, 2], 1e-6, 1 - 1e-6)
            if self.calibration == "sigmoid":
                calibrated = self.calibrator.predict_proba(
                    np.log(original / (1 - original))[:, None]
                )[:, 1]
            else:
                calibrated = self.calibrator.predict(original)
            nonharm = full[:, :2].sum(axis=1)
            for index in range(2):
                full[:, index] = np.divide(
                    full[:, index], nonharm, out=np.zeros(len(frame)), where=nonharm > 0
                ) * (1 - calibrated)
            missing = nonharm == 0
            full[missing, 1] = 1 - calibrated[missing]
            full[:, 2] = calibrated
        return full


def train_predictors(frame: pd.DataFrame, seed: int) -> tuple[Predictor, Predictor, dict[str, Any]]:
    fit = frame[frame.partition == "fit"]
    cal = frame[frame.partition == "calibration"]
    validation = frame[frame.partition == "validation"]
    observed = sorted(fit.label.unique().tolist())
    encoded = np.asarray([observed.index(label) for label in fit.label])
    estimators: dict[str, Any] = {
        "majority": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(C=1, random_state=seed)
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=100, max_depth=4, random_state=seed, n_jobs=1
        ),
        "xgboost": XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            random_state=seed,
            n_jobs=1,
            tree_method="hist",
            eval_metric="logloss",
        ),
    }
    candidates: dict[str, Predictor] = {}
    metrics: dict[str, Any] = {}
    for name, estimator in estimators.items():
        if len(observed) < 2 and name != "majority":
            metrics[name] = {"status": "NOT AVAILABLE: fitting labels have one class"}
            continue
        estimator.fit(fit[FEATURES].to_numpy(dtype=float), encoded)
        candidate = Predictor(estimator=estimator, observed_classes=observed)
        candidates[name] = candidate
        metrics[name] = predictor_metrics(validation.label, candidate.probabilities(validation))

    def rank(name: str) -> tuple[float, float, float]:
        row = metrics[name]
        return (
            row["AUPRC"] if row["AUPRC"] is not None else -1,
            row["AUROC"] if row["AUROC"] is not None else -1,
            -row["Brier"],
        )

    selected_name = max(candidates, key=rank)
    native = candidates[selected_name]
    options: dict[str, Predictor] = {"native": native}
    binary_cal = (cal.label.to_numpy() == "HARM").astype(int)
    if len(set(binary_cal)) == 2:
        risks = np.clip(native.probabilities(cal)[:, 2], 1e-6, 1 - 1e-6)
        sigmoid = LogisticRegression(C=1e6, random_state=seed)
        sigmoid.fit(np.log(risks / (1 - risks))[:, None], binary_cal)
        isotonic = IsotonicRegression(out_of_bounds="clip")
        isotonic.fit(risks, binary_cal)
        options["sigmoid"] = Predictor(native.estimator, observed, "sigmoid", sigmoid)
        options["isotonic"] = Predictor(native.estimator, observed, "isotonic", isotonic)
    cal_metrics = {
        name: predictor_metrics(validation.label, model.probabilities(validation))
        for name, model in options.items()
    }
    selected_cal = min(
        options, key=lambda name: (cal_metrics[name]["Brier"], cal_metrics[name]["ECE"])
    )
    # Deliberate audit ablation with only similarity, fit without categorical annotations.
    similarity = make_pipeline(StandardScaler(), LogisticRegression(C=1, random_state=seed))
    similarity_metrics = None
    if len(observed) >= 2:
        similarity.fit(fit[["semantic_similarity"]].to_numpy(), encoded)
        p = np.zeros((len(validation), 3))
        for index, name in enumerate(observed):
            p[:, CLASSES.index(name)] = similarity.predict_proba(
                validation[["semantic_similarity"]].to_numpy()
            )[:, index]
        similarity_metrics = predictor_metrics(validation.label, p)
    return (
        native,
        options[selected_cal],
        {
            "selected_model": selected_name,
            "selected_calibration": selected_cal,
            "validation_models": metrics,
            "validation_calibration": cal_metrics,
            "similarity_only_validation": similarity_metrics,
            "selection_partition": "validation",
            "fit_skills": sorted(fit.source_skill_id.unique().tolist()),
            "calibration_skills": sorted(cal.source_skill_id.unique().tolist()),
            "validation_skills": sorted(validation.source_skill_id.unique().tolist()),
        },
    )
