import random

import pytest

from vigil.agent.base import ExecutionRecord, Task
from vigil.agent.executor import execute_action
from vigil.evaluation.counterfactual import run_pair
from vigil.sandbox.base import SandboxState
from vigil.sandbox.mock_api import MockAPISandbox
from vigil.skills.schema import Skill


def test_pair_starts_equivalent_and_independent_with_same_random_stream():
    initial = SandboxState(http_status=503)
    skill = Skill(skill_id="retry", goal="retry", procedure=["retry"])
    task = Task(
        task_id="t",
        domain="http",
        goal="recover",
        expected_action="retry",
        allowed_actions=["retry", "request"],
    )
    observed_states, draws, objects = [], [], []

    def executor(sandbox, selected_skill, seed):
        observed_states.append(sandbox.snapshot())
        objects.append(sandbox)
        draws.append(random.random())
        action = selected_skill.procedure[0] if selected_skill else "request"
        return execute_action(
            task,
            sandbox,
            action,
            seed=seed,
            skill_id=selected_skill.skill_id if selected_skill else None,
        )

    result = run_pair(lambda: MockAPISandbox(initial), executor, skill=skill, seed=42)
    assert objects[0] is not objects[1]
    assert observed_states == [initial, initial]
    assert draws[0] == draws[1]
    assert result.initial_with == result.initial_without == initial
    assert result.delta == 2
    assert result.with_skill.metadata["condition"] == "WITH_SKILL"
    assert result.without_skill.metadata["condition"] == "WITHOUT_SKILL"
    assert initial.http_status == 503


def test_pair_rejects_reused_or_unequal_environments():
    skill = Skill(skill_id="s", goal="goal")
    env = MockAPISandbox(SandboxState())

    def executor(sandbox, selected_skill, seed):
        raise AssertionError("Must reject before execution")

    with pytest.raises(ValueError, match="independent"):
        run_pair(lambda: env, executor, skill=skill, seed=42)
    states = iter([SandboxState(http_status=503), SandboxState(http_status=401)])
    with pytest.raises(ValueError, match="identical"):
        run_pair(lambda: MockAPISandbox(next(states)), executor, skill=skill, seed=42)


def test_pair_rejects_inconsistent_record_identity():
    skill = Skill(skill_id="s", goal="goal")

    def executor(sandbox, selected_skill, seed):
        return ExecutionRecord(task_id="t", skill_id="wrong", reward=0, success=False, seed=seed)

    with pytest.raises(ValueError, match="Paired records"):
        run_pair(lambda: MockAPISandbox(SandboxState()), executor, skill=skill, seed=42)
