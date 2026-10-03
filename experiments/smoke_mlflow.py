"""Infrastructure smoke log only. Dummy values are not scientific research results."""

import io
import sys
from pathlib import Path

import mlflow

from vigil.utils.config import load_config
from vigil.utils.logging import configure_logging
from vigil.utils.seeds import seed_everything
from vigil.utils.version import capture_versions


def main() -> None:
    # MLflow prints Unicode run links; Windows redirected stdout may default to cp1252.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "configs/base.yaml")
    configure_logging(config.log_level)
    seed_everything(config.random_seed)
    provenance = capture_versions(repo_root=root)
    mlflow.set_tracking_uri(config.tracking_uri)
    mlflow.set_experiment("VIGIL-AEM-infrastructure-smoke")
    with mlflow.start_run(run_name="bootstrap-smoke"):
        mlflow.set_tags(
            {
                "purpose": "infrastructure_smoke_only",
                "scientific_result": "false",
                "project": config.project_name,
            }
        )
        mlflow.log_params(
            {
                "project_name": config.project_name,
                "python_version": provenance.python_version,
                "git_commit": provenance.git_commit or "unavailable",
                "random_seed": config.random_seed,
                "dummy_parameter": "bootstrap",
            }
        )
        mlflow.log_metric("dummy_metric", 1.0)
        mlflow.log_dict(provenance.model_dump(), "provenance.json")
    print("Infrastructure smoke run logged; no research result produced.")


if __name__ == "__main__":
    main()
