import math

import pytest
from pydantic import ValidationError

from vigil.aem.schema import AdverseExperience
from vigil.agent.base import ExecutionRecord, Task
from vigil.skills.schema import Skill


def adverse(**changes):
    return AdverseExperience(
        **{
            "event_id": "event",
            "severity": 0.5,
            "causal_score": 0.5,
            "diagnosis_confidence": 0.5,
            **changes,
        }
    )


@pytest.mark.parametrize("field", ["severity", "causal_score", "diagnosis_confidence"])
@pytest.mark.parametrize("value", [-0.01, 1.01, math.nan, math.inf])
def test_adverse_rejects_invalid_ranges(field, value):
    with pytest.raises(ValidationError):
        adverse(**{field: value})


@pytest.mark.parametrize("value", [0, 1])
def test_adverse_accepts_boundaries(value):
    event = adverse(severity=value, causal_score=value, diagnosis_confidence=value)
    assert AdverseExperience.model_validate_json(event.model_dump_json()) == event


def test_assignment_is_validated():
    event = adverse()
    with pytest.raises(ValidationError):
        event.severity = 2


@pytest.mark.parametrize("field", ["success_count", "failure_count"])
def test_skill_counts_cannot_be_negative(field):
    with pytest.raises(ValidationError):
        Skill(skill_id="s", goal="goal", **{field: -1})


def test_skill_mutable_defaults_are_independent():
    first = Skill(skill_id="first", goal="goal")
    second = Skill(skill_id="second", goal="goal")
    first.procedure.append("retry")
    assert second.procedure == []


def test_task_requires_identity_and_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        Task(task_id="", domain="http", goal="retry", expected_action="retry")
    with pytest.raises(ValidationError):
        Task(task_id="t", domain="http", goal="retry", expected_action="retry", secret="x")


def test_execution_record_roundtrip_and_optional_skill():
    record = ExecutionRecord(task_id="t", reward=-1, success=False, seed=42)
    assert record.skill_id is None
    assert ExecutionRecord.model_validate_json(record.model_dump_json()) == record
    with pytest.raises(ValidationError):
        ExecutionRecord(task_id="t", reward=math.nan, success=False, seed=42)
