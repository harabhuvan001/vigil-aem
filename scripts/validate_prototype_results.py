"""Validate every mandatory artifact and its measured-execution provenance."""

import argparse
import json
from pathlib import Path

from vigil.evaluation.validate_artifacts import validate_results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("results/final_prototype"))
    args = parser.parse_args()
    print(json.dumps(validate_results(args.root, Path(__file__).resolve().parents[1]), indent=2))


if __name__ == "__main__":
    main()
