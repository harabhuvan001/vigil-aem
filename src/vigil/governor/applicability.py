"""Literal precondition check for bootstrap fixtures, not semantic applicability."""

from vigil.agent.base import Task
from vigil.skills.schema import Skill


def satisfies_preconditions(task: Task, skill: Skill) -> bool:
    """Each named fact must exist and be exactly True; unknown facts fail closed."""
    return all(task.state.get(condition) is True for condition in skill.preconditions)
