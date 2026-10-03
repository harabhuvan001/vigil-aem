"""Task and execution schemas for future agents."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    task_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    state: dict[str, JsonValue] = Field(default_factory=dict)
    allowed_actions: list[str] = Field(default_factory=list)
    expected_action: str = Field(min_length=1)


class ExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    task_id: str = Field(min_length=1)
    skill_id: str | None = None
    reward: float = Field(allow_inf_nan=False)
    success: bool
    seed: int = Field(ge=0, le=2**32 - 1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
