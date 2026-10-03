"""Policy, leakage and statistical unit controls; these fixtures are not research results."""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from vigil.aem.memory import AdverseExperienceMemory, AdverseMemoryEvent
from vigil.agent.policy import choose_action, goal_action
from vigil.benchmark.dataset import load_corpus
from vigil.benchmark.schema import Category, Domain
from vigil.evaluation.prototype import Recorder, execute_governed, transfer_label
from vigil.evaluation.prototype_schema import (
    PrototypeConfig,
    digest,
    expose,
    load_split,
    public_view,
)
from vigil.evaluation.statistics import paired_statistics
from vigil.evaluation.validate_artifacts import equal_metrics, validate_results
from vigil.governor.applicability import inspect_preconditions
from vigil.governor.policy import risk_decision
from vigil.governor.risk import FEATURES, predictor_metrics, train_predictors
from vigil.governor.shift import inspect_shift
from vigil.sandbox.skillshift import SkillShiftFixture

ROOT = Path(__file__).resolve().parents[2]
SKILLS, TASKS, FIXTURES = load_corpus(ROOT / "benchmark")
CONFIG = PrototypeConfig.model_validate_json((ROOT / "configs/fast_prototype.json").read_text())


@pytest.mark.parametrize("task", TASKS, ids=[task.task_id for task in TASKS])
def test_policy_access_boundary_and_factual_preconditions(task):
    source = next(skill for skill in SKILLS if skill.skill_id == task.source_skill_id)
    view = public_view(task, task.initial_state)
    assert set(view.model_dump()) == {
        "domain",
        "goal",
        "state",
        "allowed_actions",
        "protected_scopes",
    }
    assert view.protected_scopes == task.metadata.protected_scopes
    assert goal_action(view) in task.accepted_actions
    assert choose_action(view, None, similarity=0.99, similarity_threshold=0.8) == goal_action(view)
    skill = expose(source)
    assert choose_action(view, skill, similarity=0.99, similarity_threshold=0.8) == "apply_primary"
    assert choose_action(view, skill, similarity=0.1, similarity_threshold=0.8) == goal_action(view)
    applicability = inspect_preconditions(view, skill)
    shift = inspect_shift(view, skill)
    assert 0 <= applicability.score <= 1 and 0 <= shift.score <= 1
    bad = task.transfer_category in {Category.NEAR, Category.NEGATIVE, Category.DECEPTIVE}
    assert bool(applicability.violated) is bad
    assert bool(shift.score) is bad
    # Evaluation labels and expected states are deliberately altered; public view cannot change.
    corrupted = task.model_copy(deep=True)
    corrupted.metadata.display_hint = "invented hint"
    corrupted.accepted_actions.clear()
    corrupted.expected_final_state.scopes.clear()
    assert public_view(corrupted, task.initial_state) == view


def event(**changes):
    return AdverseMemoryEvent(
        **{
            "event_id": "unit-event",
            "skill_id": "unit-skill",
            "task_id": "unit-task",
            "context": {"primary_protected": True},
            "failure": "unit failure",
            "severity": 0.8,
            "causal_score": 0.5,
            "diagnosis_confidence": 0.5,
            "warning_conditions": ["primary_protected"],
            "source_execution_ids": ["without", "with"],
            "provenance": {"origin": "unit fixture only"},
            **changes,
        }
    )


@pytest.mark.parametrize("field", ["severity", "causal_score", "diagnosis_confidence"])
@pytest.mark.parametrize("value", [-0.1, 1.1, math.nan, math.inf])
def test_aem_unit_scores_are_validated(field, value):
    with pytest.raises(ValidationError):
        event(**{field: value})


def test_aem_admission_requires_causal_reliable_evidence_and_never_deletes_skill():
    full = AdverseExperienceMemory("full")
    naive = AdverseExperienceMemory("naive")
    noncausal = event(causal_score=0)
    assert not full.admit(noncausal)
    assert naive.admit(noncausal)
    memory_event = event()
    assert full.admit(memory_event)
    assert not full.admit(memory_event)
    assert memory_event.priority == pytest.approx(0.2)
    risk, hits = full.risk("unit-skill", {"primary_protected": True}, {"unit-task": 1.0})
    assert risk == pytest.approx(0.2) and hits == ["unit-event"]
    assert full.risk("unrelated", {"primary_protected": True}, {"unit-task": 1}) == (0.0, [])
    assert full.events[0].status == "active"


def test_grouped_split_is_frozen_disjoint_and_covers_all_variants():
    split = load_split(ROOT / "configs/fast_prototype_splits.json", SKILLS)
    for skill in SKILLS:
        variants = [task for task in TASKS if task.source_skill_id == skill.skill_id]
        assert len(variants) == 5
        assert len({split.partition(task.source_skill_id) for task in variants}) == 1
    schema = json.loads((ROOT / "configs/fast_prototype_splits.json").read_text())
    schema["test"][0] = schema["fit"][0]
    with pytest.raises(ValidationError):
        type(split).model_validate(schema)


def test_unit_metrics_absent_classes_and_probability_quality():
    result = predictor_metrics(["HARM", "NEUTRAL"], np.array([[0, 0, 1], [0, 1, 0]]))
    assert result["AUROC"] == result["AUPRC"] == 1
    assert result["Brier"] == result["ECE"] == 0
    assert result["absent_class_metrics"] == ["HELP"]
    one = predictor_metrics(["NEUTRAL"], np.array([[0, 1, 0]]))
    assert one["AUROC"] is None and one["AUPRC"] is None


def unit_training_frame():
    # Explicitly synthetic unit data, never used by the experiment or report.
    rows = []
    for partition in ["fit", "calibration", "validation", "test"]:
        for index in range(12):
            harm = index % 2
            row = {name: 0.0 for name in FEATURES}
            row.update(
                {
                    "semantic_similarity": 0.8,
                    "applicability_score": 1 - harm,
                    "failed_precondition_count": harm,
                    "shift_score": float(harm),
                    "label": "HARM" if harm else "NEUTRAL",
                    "partition": partition,
                    "source_skill_id": f"unit-{partition}-{index}",
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def test_model_selection_cannot_see_heldout_labels_or_features():
    frame = unit_training_frame()
    native, calibrated, selected = train_predictors(frame, 42)
    changed = frame.copy()
    changed.loc[changed.partition == "test", FEATURES] = 987.0
    changed.loc[changed.partition == "test", "label"] = "HELP"
    other_native, other_calibrated, other = train_predictors(changed, 42)
    assert selected == other
    assert np.allclose(native.probabilities(frame), other_native.probabilities(frame))
    assert np.allclose(calibrated.probabilities(frame), other_calibrated.probabilities(frame))


def test_paired_cluster_statistics_reproduce_and_do_not_count_variants_as_clusters():
    frame = pd.DataFrame(
        {
            "source_skill_id": ["a", "a", "b", "b"],
            "reward_difference": [2, 2, -2, -2],
            "success_without": [0, 0, 1, 1],
            "success_with": [1, 1, 0, 0],
        }
    )
    first = paired_statistics(frame, seed=42, bootstrap=100, permutations=100)
    assert first == paired_statistics(frame, seed=42, bootstrap=100, permutations=100)
    assert first["cluster_count"] == 2 and first["task_count"] == 4
    assert first["mean_reward_effect"] == 0 and first["mcnemar_exact_p"] == 1


def test_three_way_policy_and_transfer_boundaries():
    assert [risk_decision(risk, 0.2, 0.8) for risk in [0.1, 0.5, 0.9]] == [
        "USE",
        "VERIFY",
        "REJECT",
    ]
    assert [transfer_label(gain, 0.1) for gain in [0.2, 0.1, 0, -0.1, -0.2]] == [
        "HELP",
        "NEUTRAL",
        "NEUTRAL",
        "NEUTRAL",
        "HARM",
    ]
    with pytest.raises(ValueError):
        risk_decision(0.5, 0.8, 0.2)


def test_reset_clone_evaluation_and_ledger_are_environment_derived(tmp_path):
    task = next(
        task
        for task in TASKS
        if task.metadata.operation == "fs_create" and task.transfer_category == Category.NEGATIVE
    )
    fixture = next(f for f in FIXTURES if f.fixture_id == task.fixture_id)
    with SkillShiftFixture(fixture) as environment:
        with environment.clone() as other:
            assert digest(other.clone_state()) == digest(environment.observe())
            assert other.execute("apply_primary")
            assert not other.evaluate(task, "apply_primary").success
            assert environment.observe() == task.initial_state
    recorder = Recorder(tmp_path, FIXTURES, CONFIG, "unit-checksum", "unit-commit", False)
    failed = recorder.run(task, "apply_primary", "UNIT", "unit", True)
    assert not failed.success and failed.reward == -1
    resumed = Recorder(tmp_path, FIXTURES, CONFIG, "unit-checksum", "unit-commit", True)
    assert resumed.run(task, "apply_primary", "UNIT", "unit", True) == failed
    with pytest.raises(ValueError, match="action/state changed"):
        resumed.run(task, "apply_secondary", "UNIT", "unit", True)


def test_artifact_validator_rejects_incomplete_results(tmp_path):
    with pytest.raises(ValueError, match="Missing/empty"):
        validate_results(tmp_path, ROOT)


def test_artifact_metrics_preserve_undefined_denominators_across_formats():
    assert equal_metrics(pd.Series([None, None]), pd.Series([np.nan, np.nan]))
    assert equal_metrics(pd.Series([None, 0.5]), pd.Series([np.nan, 0.5]))
    assert not equal_metrics(pd.Series([None, 0.5]), pd.Series([0.0, 0.5]))


@pytest.mark.parametrize("domain", list(Domain))
@pytest.mark.parametrize("category", [Category.EXACT, Category.NEGATIVE])
def test_uncertain_verification_executes_an_independent_candidate(domain, category, tmp_path):
    # Explicit unit injection exercises VERIFY even when measured calibrated risks are extreme.
    # This unit control is never exported as an experimental result.
    task = next(t for t in TASKS if t.domain == domain and t.transfer_category == category)
    skill = next(s for s in SKILLS if s.skill_id == task.source_skill_id)
    recorder = Recorder(tmp_path, FIXTURES, CONFIG, "unit-checksum", "unit-commit", False)
    result = execute_governed(
        task, skill, 1.0, 0.5, 0.5, "S5", "unit", {"low": 0.4, "high": 0.9}, recorder
    )
    assert result["verified"] and result["decision"] == "VERIFY"
    assert result["success"]
    assert result["candidate_used"] is (category == Category.EXACT)
    assert len(recorder.trials) == 2
    verification = recorder.trials[f"verify-unit:S5:{task.task_id}"]
    execution = recorder.trials[f"unit:S5:{task.task_id}"]
    assert verification.initial_state_hash == execution.initial_state_hash
    assert verification.success is (category == Category.EXACT)
