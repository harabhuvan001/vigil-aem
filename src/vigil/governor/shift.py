"""Interpretable factual context-shift baseline for the finite benchmark."""

from pydantic import Field

from vigil.agent.policy import goal_action
from vigil.evaluation.prototype_schema import ExposedSkill, PublicTask, StrictModel


class Shift(StrictModel):
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    signals: dict[str, bool]
    unknown: list[str]


def inspect_shift(view: PublicTask, skill: ExposedSkill) -> Shift:
    current = view.state.scopes.get("primary")
    source = skill.source_initial.scopes.get("primary")
    signals = {
        "domain_mismatch": view.domain != skill.domain,
        "tool_mismatch": skill.candidate_action not in view.allowed_actions,
        "permission_mismatch": "primary" in view.protected_scopes,
        "resource_type_mismatch": current is not None and type(current) is not type(source),
        "binding_mismatch": "primary" not in view.state.scopes,
        "protection_state_mismatch": bool(view.protected_scopes),
        "goal_intent_mismatch": goal_action(view) not in {skill.candidate_action, "noop"},
    }
    return Shift(
        score=sum(signals.values()) / len(signals),
        signals=signals,
        unknown=["api_version", "arbitrary_operation_equivalence"],
    )
