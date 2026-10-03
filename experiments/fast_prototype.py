"""Run the measured fast prototype; generated outputs and fitted models remain untracked."""

import argparse
from pathlib import Path

from vigil.evaluation.run_prototype import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/final_prototype"))
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse recorded executions with matching state/action provenance",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate reports from saved artifacts; no trials",
    )
    args = parser.parse_args()
    run_experiment(
        Path(__file__).resolve().parents[1],
        args.output.resolve(),
        resume=args.resume,
        report_only=args.report_only,
    )


if __name__ == "__main__":
    main()
