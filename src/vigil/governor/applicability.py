"""Literal precondition check for bootstrap fixtures, not semantic applicability."""

from pydantic import Field

from vigil.agent.base import Task
from vigil.agent.policy import goal_action
from vigil.benchmark.schema import APIState, GitState, Scope
from vigil.evaluation.prototype_schema import ExposedSkill, PublicTask, StrictModel
from vigil.skills.schema import Skill


class Applicability(StrictModel):
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    satisfied: list[str]
    violated: list[str]
    unknown: list[str]


def inspect_preconditions(view: PublicTask, skill: ExposedSkill) -> Applicability:
    candidate = skill.candidate_action
    scope: Scope = "primary" if candidate == "apply_primary" else "secondary"
    atom = view.state.scopes.get(scope)
    source = skill.source_initial.scopes.get("primary")
    completed = skill.source_completed.scopes.get("primary")
    facts: dict[str, bool | None] = {
        "domain_match": view.domain == skill.domain,
        "tool_allowed": candidate in view.allowed_actions,
        "bound_scope_exists": atom is not None,
        "resource_authorized": scope not in view.protected_scopes,
        "source_prestate_or_completed": atom == source or atom == completed,
        "goal_binding_matches": goal_action(view) in {candidate, "noop"},
    }
    if isinstance(source, APIState):
        facts["api_status_precondition"] = isinstance(atom, APIState) and (
            atom.status == source.status or atom == completed
        )
        facts["authentication_precondition"] = isinstance(atom, APIState) and (
            atom.token == source.token or atom == completed
        )
    if isinstance(source, GitState):
        facts["git_head_precondition"] = isinstance(atom, GitState) and (
            atom.head == source.head or atom == completed
        )
        facts["git_index_precondition"] = isinstance(atom, GitState) and (
            atom.index == source.index or atom == completed
        )
    satisfied = [key for key, value in facts.items() if value is True]
    violated = [key for key, value in facts.items() if value is False]
    unknown = [key for key, value in facts.items() if value is None]
    return Applicability(
        score=len(satisfied) / len(facts), satisfied=satisfied, violated=violated, unknown=unknown
    )


def satisfies_preconditions(task: Task, skill: Skill) -> bool:
    """Each named fact must exist and be exactly True; unknown facts fail closed."""
    return all(task.state.get(condition) is True for condition in skill.preconditions)
