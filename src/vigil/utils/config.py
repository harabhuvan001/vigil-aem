"""Typed YAML configuration with a small, explicitly permitted environment overlay."""

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ResearchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str = "VIGIL-AEM"
    random_seed: int = Field(default=42, ge=0, le=2**32 - 1)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    tracking_uri: str = "http://localhost:5000"
    transfer_epsilon: float = Field(default=0.01, ge=0, allow_inf_nan=False)


def load_config(path: str | Path, *, use_environment: bool = True) -> ResearchConfig:
    with Path(path).open(encoding="utf-8") as handle:
        values = yaml.safe_load(handle)
    if not isinstance(values, dict):
        raise ValueError("Configuration must be a YAML mapping")
    if use_environment:
        for environment_key, field in (
            ("VIGIL_RANDOM_SEED", "random_seed"),
            ("VIGIL_LOG_LEVEL", "log_level"),
            ("MLFLOW_TRACKING_URI", "tracking_uri"),
        ):
            value = os.environ.get(environment_key)
            if value is not None:
                values[field] = value
    return ResearchConfig.model_validate(values)
