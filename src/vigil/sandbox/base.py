"""In-memory sandbox contract; no host filesystem, network, or database access."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field


class SandboxState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    http_status: int = Field(default=200, ge=100, le=599)
    files: dict[str, str] = Field(default_factory=dict)
    protected_files: list[str] = Field(default_factory=list)
    transaction_active: bool = False
    rows: dict[str, int] = Field(default_factory=dict)


class Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reward: float = Field(allow_inf_nan=False)
    success: bool
    severity: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)


class Sandbox(ABC):
    def __init__(self, initial_state: SandboxState) -> None:
        self._initial_state = initial_state.model_copy(deep=True)
        self._state = initial_state.model_copy(deep=True)

    def snapshot(self) -> SandboxState:
        return self._state.model_copy(deep=True)

    def reset(self) -> None:
        self._state = self._initial_state.model_copy(deep=True)

    @abstractmethod
    def execute(self, action: str) -> Outcome:
        """Execute a fixture action in memory only."""
