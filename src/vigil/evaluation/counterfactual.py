"""Paired toy execution skeleton with independent, equivalent initial environments."""

from collections.abc import Callable
from enum import StrEnum

from pydantic import BaseModel

from vigil.agent.base import ExecutionRecord
from vigil.evaluation.metrics import transfer_delta
from vigil.sandbox.base import Sandbox, SandboxState
from vigil.skills.schema import Skill
from vigil.utils.seeds import seed_everything


class Condition(StrEnum):
    WITH_SKILL = "WITH_SKILL"
    WITHOUT_SKILL = "WITHOUT_SKILL"


class PairedResult(BaseModel):
    with_skill: ExecutionRecord
    without_skill: ExecutionRecord
    initial_with: SandboxState
    initial_without: SandboxState

    @property
    def delta(self) -> float:
        return transfer_delta(self.with_skill.reward, self.without_skill.reward)


Executor = Callable[[Sandbox, Skill | None, int], ExecutionRecord]


def run_pair(
    sandbox_factory: Callable[[], Sandbox],
    executor: Executor,
    *,
    skill: Skill,
    seed: int,
) -> PairedResult:
    with_env, without_env = sandbox_factory(), sandbox_factory()
    if with_env is without_env:
        raise ValueError("Factory must return independent sandbox instances")
    with_env.reset()
    without_env.reset()
    initial_with, initial_without = with_env.snapshot(), without_env.snapshot()
    if initial_with != initial_without:
        raise ValueError("Counterfactual initial states must be identical")
    seed_everything(seed)
    with_record = executor(with_env, skill.model_copy(deep=True), seed)
    seed_everything(seed)
    without_record = executor(without_env, None, seed)
    if (
        with_record.task_id != without_record.task_id
        or with_record.skill_id != skill.skill_id
        or without_record.skill_id is not None
        or with_record.seed != seed
        or without_record.seed != seed
    ):
        raise ValueError("Paired records must identify the same task, seed, and skill condition")
    with_record = with_record.model_copy(deep=True)
    without_record = without_record.model_copy(deep=True)
    with_record.metadata["condition"] = Condition.WITH_SKILL.value
    without_record.metadata["condition"] = Condition.WITHOUT_SKILL.value
    return PairedResult(
        with_skill=with_record,
        without_skill=without_record,
        initial_with=initial_with,
        initial_without=initial_without,
    )
