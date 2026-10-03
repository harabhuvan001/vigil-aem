import pytest

from vigil.agent.base import Task
from vigil.governor.applicability import satisfies_preconditions
from vigil.skills.schema import Skill


@pytest.mark.parametrize(
    "state,expected",
    [
        ({"transaction": True}, True),
        ({"transaction": False}, False),
        ({}, False),
        ({"transaction": "true"}, False),
        ({"transaction": 1}, False),
    ],
)
def test_only_inspected_boolean_facts_satisfy_preconditions(state, expected):
    task = Task(task_id="t", domain="sql", goal="update", state=state, expected_action="update")
    skill = Skill(skill_id="s", goal="update", preconditions=["transaction"])
    assert satisfies_preconditions(task, skill) is expected


def test_no_preconditions_is_vacuously_satisfied():
    task = Task(task_id="t", domain="http", goal="request", expected_action="request")
    assert satisfies_preconditions(task, Skill(skill_id="s", goal="request"))
