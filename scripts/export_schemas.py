"""Regenerate public JSON schemas from the canonical Pydantic models."""

from pathlib import Path

from pydantic import BaseModel

from vigil.aem.schema import AdverseExperience
from vigil.agent.base import ExecutionRecord, Task
from vigil.skills.schema import Skill


def main() -> None:
    import json

    target = Path(__file__).resolve().parents[1] / "benchmark/schemas"
    target.mkdir(parents=True, exist_ok=True)
    schemas: dict[str, type[BaseModel]] = {
        "skill": Skill,
        "task": Task,
        "execution_record": ExecutionRecord,
        "adverse_experience": AdverseExperience,
    }
    for name, model in schemas.items():
        (target / f"{name}.json").write_text(
            json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
