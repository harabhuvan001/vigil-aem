"""Versioned procedural skill schema; no learned behavior."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    skill_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    preconditions: list[str] = Field(default_factory=list)
    procedure: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    status: Literal["draft", "active", "retired"] = "draft"
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
