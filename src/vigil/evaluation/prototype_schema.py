"""Validated experiment configuration and oracle-free agent access contracts."""

import hashlib
import json
import re
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vigil.benchmark.schema import Action, Domain, Scope, SourceSkill, State, TransferTask


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class PrototypeConfig(StrictModel):
    version: str
    seed: int = Field(ge=0)
    epsilon: float = Field(ge=0, allow_inf_nan=False)
    similarity_threshold: float = Field(ge=-1, le=1)
    embedding_model: str
    embedding_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    embedding_text_version: str
    prompt_version: str
    max_tool_steps: Literal[1]
    bootstrap_repetitions: int = Field(ge=100)
    permutation_repetitions: int = Field(ge=100)
    verification_cost: float = Field(ge=0)
    safe_rejection_cost: float = Field(ge=0)


class PublicTask(StrictModel):
    domain: Domain
    goal: str
    state: State
    allowed_actions: list[Action]
    protected_scopes: list[Scope]


class ExposedSkill(StrictModel):
    skill_id: str
    domain: Domain
    goal: str
    preconditions: list[str]
    procedure: list[str]
    postconditions: list[str]
    source_initial: State
    source_completed: State
    candidate_action: Action


def public_view(task: TransferTask, state: State) -> PublicTask:
    # Authoritative goal text is inspectable; evaluator metadata and labels are excluded.
    protected: list[Scope] = []
    for scope in ("primary", "secondary"):
        if re.search(rf"\b{scope} is reserved\b", task.natural_language_goal, re.IGNORECASE):
            protected.append(scope)
    return PublicTask(
        domain=task.domain,
        goal=task.natural_language_goal,
        state=state.model_copy(deep=True),
        allowed_actions=list(task.allowed_actions),
        protected_scopes=protected,
    )


def expose(skill: SourceSkill) -> ExposedSkill:
    return ExposedSkill(
        skill_id=skill.skill_id,
        domain=skill.domain,
        goal=skill.goal,
        preconditions=list(skill.preconditions),
        procedure=list(skill.procedure),
        postconditions=list(skill.postconditions),
        source_initial=skill.source_context.initial_state,
        source_completed=skill.source_context.expected_final_state,
        candidate_action=skill.source_context.expected_action,
    )


def digest(model: BaseModel) -> str:
    data = json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class SplitManifest(StrictModel):
    seed: int
    grouping: Literal["source_skill_id"] = "source_skill_id"
    fit: list[str]
    calibration: list[str]
    validation: list[str]
    test: list[str]

    @model_validator(mode="after")
    def disjoint(self) -> Self:
        groups = [self.fit, self.calibration, self.validation, self.test]
        flattened = [item for group in groups for item in group]
        if len(flattened) != 40 or len(set(flattened)) != 40:
            raise ValueError("Split requires 40 unique, disjoint source skills")
        if [len(group) for group in groups] != [12, 12, 8, 8]:
            raise ValueError("Expected 12 fit / 12 calibration / 8 validation / 8 test skills")
        return self

    def partition(self, skill_id: str) -> str:
        for name in ("fit", "calibration", "validation", "test"):
            if skill_id in getattr(self, name):
                return name
        raise ValueError("Unknown split skill")


def load_split(path: Path, skills: list[SourceSkill]) -> SplitManifest:
    split = SplitManifest.model_validate_json(path.read_text(encoding="utf-8"))
    if set(split.fit + split.calibration + split.validation + split.test) != {
        s.skill_id for s in skills
    }:
        raise ValueError("Split does not match frozen corpus")
    expected = path.with_suffix(".sha256").read_text(encoding="ascii").strip()
    if expected != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("Split checksum mismatch")
    return split
