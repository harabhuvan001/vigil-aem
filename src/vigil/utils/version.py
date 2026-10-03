"""Capture reproducibility metadata without reading credentials or downloading models."""

import platform
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    python_version: str
    operating_system: str
    package_versions: dict[str, str] = Field(default_factory=dict)
    git_commit: str | None = None
    model_identifier: str | None = None
    model_revision: str | None = None


def capture_versions(
    *,
    repo_root: Path | None = None,
    model_identifier: str | None = None,
    model_revision: str | None = None,
) -> Provenance:
    root = repo_root or Path.cwd()
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    return Provenance(
        python_version=platform.python_version(),
        operating_system=f"{sys.platform}: {platform.platform()}",
        package_versions={
            str(d.metadata["Name"]): d.version for d in distributions() if d.metadata["Name"]
        },
        git_commit=commit,
        model_identifier=model_identifier,
        model_revision=model_revision,
    )
