"""Strict, versioned SkillShiftBench contracts, separate from bootstrap schemas."""

import re
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Domain(StrEnum):
    FILESYSTEM = "filesystem"
    API = "mock_http_api"
    SQL = "sql_database"
    GIT = "git_operations"


class Category(StrEnum):
    EXACT = "EXACT"
    NEAR = "NEAR"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    DECEPTIVE = "DECEPTIVE"


Scope = Literal["primary", "secondary"]
Action = Literal["apply_primary", "apply_secondary", "noop"]
Identifier = Annotated[str, Field(min_length=1, pattern=r"^[a-z0-9_.-]+$")]
Text = Annotated[str, Field(min_length=1)]


def safe_path(value: str) -> str:
    """Allow only portable relative paths; never repository metadata or traversal."""
    if not re.fullmatch(r"[a-z][a-z0-9_.-]*(/[a-z][a-z0-9_.-]*)*", value):
        raise ValueError("Path must be a portable relative fixture path")
    if any(part == ".git" or part in {"con", "nul", "aux", "prn"} for part in value.split("/")):
        raise ValueError("Reserved fixture path")
    return value


class FileState(Contract):
    files: dict[str, str] = Field(default_factory=dict)
    directories: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def paths(self) -> Self:
        for name in [*self.files, *self.directories]:
            safe_path(name)
        if len(set(self.directories)) != len(self.directories):
            raise ValueError("Duplicate directory")
        if set(self.files) & set(self.directories):
            raise ValueError("File and directory paths overlap")
        return self


class APIState(Contract):
    resources: dict[str, str] = Field(default_factory=dict)
    status: int = Field(default=0, ge=0, le=599)
    token: Literal["valid", "expired"] = "valid"
    etag: int = Field(default=1, ge=1)
    cursor: int = Field(default=0, ge=0)
    location: Literal["", "/canonical"] = ""


class SQLState(Contract):
    rows: dict[str, str]


class GitState(Contract):
    base: dict[str, str]
    files: dict[str, str]
    index: dict[str, str]
    head: Literal["main", "topic"] = "main"
    branches: list[Literal["main", "topic"]] = Field(default=["main"])
    tags: list[Literal["v1"]] = Field(default_factory=list)
    commits: list[Literal["base", "skillshift"]] = Field(default=["base"])

    @model_validator(mode="after")
    def repository(self) -> Self:
        for name in {*self.base, *self.files, *self.index}:
            safe_path(name)
        if self.head not in self.branches or "main" not in self.branches:
            raise ValueError("HEAD must reference an existing branch")
        if self.commits not in [["base"], ["base", "skillshift"]]:
            raise ValueError("Unsupported fixture history")
        for values in (self.branches, self.tags):
            if values != sorted(set(values)):
                raise ValueError("Refs must be unique and sorted")
        return self


Atom = FileState | APIState | SQLState | GitState


class FilesystemState(Contract):
    domain: Literal["filesystem"] = "filesystem"
    scopes: dict[Scope, FileState]


class HTTPState(Contract):
    domain: Literal["mock_http_api"] = "mock_http_api"
    scopes: dict[Scope, APIState]


class DatabaseState(Contract):
    domain: Literal["sql_database"] = "sql_database"
    scopes: dict[Scope, SQLState]


class RepositoryState(Contract):
    domain: Literal["git_operations"] = "git_operations"
    scopes: dict[Scope, GitState]


State = Annotated[
    FilesystemState | HTTPState | DatabaseState | RepositoryState, Field(discriminator="domain")
]


class RewardRule(Contract):
    rule_id: Literal["exact_action_and_state_v1"] = "exact_action_and_state_v1"
    success_reward: Literal[1] = 1
    failure_reward: Literal[-1] = -1
    require_full_state_equality: Literal[True] = True


class Metadata(Contract):
    benchmark_version: Literal["0.1"] = "0.1"
    family_id: Identifier
    operation: Identifier
    context_change: Text
    protected_scopes: list[Scope] = Field(default_factory=list)
    display_hint: Text
    seed: Literal[0] = 0
    split: Literal["unassigned"] = "unassigned"


class Fixture(Contract):
    fixture_id: Identifier
    domain: Domain
    operation: Identifier
    initial_state: State
    reset_id: Literal["recreate_owned_state_v1"] = "recreate_owned_state_v1"

    @model_validator(mode="after")
    def matching_domain(self) -> Self:
        if self.initial_state.domain != self.domain or not self.initial_state.scopes:
            raise ValueError("Fixture state must be nonempty and match domain")
        return self


class SourceContext(Contract):
    initial_state: State
    expected_final_state: State
    allowed_actions: list[Action] = Field(min_length=1)
    expected_action: Action
    fixture_id: Identifier


class Provenance(Contract):
    origin: Literal["synthetic_authored_catalog"] = "synthetic_authored_catalog"
    specification: Literal["docs/SKILLSHIFT_V0_1.md"] = "docs/SKILLSHIFT_V0_1.md"
    generator_version: Literal["skillshift_catalog_v1"] = "skillshift_catalog_v1"
    license: Literal["MIT"] = "MIT"
    seed: Literal[0] = 0


class SourceSkill(Contract):
    skill_id: Identifier
    domain: Domain
    goal: Text
    preconditions: list[Text] = Field(min_length=1)
    procedure: list[Text] = Field(min_length=1)
    postconditions: list[Text] = Field(min_length=1)
    source_task_id: Identifier
    source_context: SourceContext
    provenance: Provenance
    version: Literal["0.1"] = "0.1"

    @model_validator(mode="after")
    def context_domain(self) -> Self:
        context = self.source_context
        if context.initial_state.domain != self.domain:
            raise ValueError("Source context domain mismatch")
        if context.expected_final_state.domain != self.domain:
            raise ValueError("Source outcome domain mismatch")
        if context.expected_action not in context.allowed_actions:
            raise ValueError("Source expected action must be allowed")
        return self


class TransferTask(Contract):
    task_id: Identifier
    source_skill_id: Identifier
    domain: Domain
    transfer_category: Category
    natural_language_goal: Text
    initial_state: State
    allowed_actions: list[Action] = Field(min_length=1)
    accepted_actions: list[Action] = Field(min_length=1)
    expected_final_state: State
    reward_rules: RewardRule
    severity_if_failed: float = Field(ge=0, le=1, allow_inf_nan=False, strict=True)
    fixture_id: Identifier
    metadata: Metadata

    @field_validator("allowed_actions", "accepted_actions")
    @classmethod
    def unique_actions(cls, actions: list[Action]) -> list[Action]:
        if len(actions) != len(set(actions)):
            raise ValueError("Duplicate action")
        return actions

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.initial_state.domain != self.domain
            or self.expected_final_state.domain != self.domain
        ):
            raise ValueError("Task states must match domain")
        if not set(self.accepted_actions) <= set(self.allowed_actions):
            raise ValueError("Accepted actions must be allowed")
        if self.initial_state.scopes.keys() != self.expected_final_state.scopes.keys():
            raise ValueError("Outcome scopes must match initial scopes")
        for scope in self.metadata.protected_scopes:
            if scope not in self.initial_state.scopes:
                raise ValueError("Protected scope missing")
            if self.initial_state.scopes[scope] != self.expected_final_state.scopes[scope]:
                raise ValueError("Protected scope must be preserved")
        return self
