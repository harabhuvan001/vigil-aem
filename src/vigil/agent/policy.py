"""A fixed deterministic instrumentation agent; this is not an LLM."""

import re

from vigil.benchmark.schema import Action
from vigil.evaluation.prototype_schema import ExposedSkill, PublicTask


def goal_action(view: PublicTask) -> Action:
    text = view.goal.lower()
    if "already completed" in text and "do not change any state" in text:
        return "noop"
    scope = (
        "secondary" if re.search(r"\bin (?:the )?secondary(?: scope| only)\b", text) else "primary"
    )
    if scope in view.state.scopes:
        action: Action = "apply_secondary" if scope == "secondary" else "apply_primary"
        if action in view.allowed_actions:
            return action
    return "noop"


def choose_action(
    view: PublicTask, skill: ExposedSkill | None, *, similarity: float, similarity_threshold: float
) -> Action:
    """Same function for both paired conditions; only skill exposure differs."""
    if skill is not None and similarity >= similarity_threshold:
        if skill.candidate_action in view.allowed_actions:
            return skill.candidate_action
    return goal_action(view)
