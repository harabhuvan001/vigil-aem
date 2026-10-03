"""Validate the frozen release, or rebuild it in a separate review directory."""

import argparse
from collections import Counter
from pathlib import Path

from vigil.benchmark.dataset import load_corpus, verify_checksums, write_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1] / "benchmark"
    )
    parser.add_argument(
        "--build", action="store_true", help="Create data; refuse changed existing files"
    )
    args = parser.parse_args()
    if args.build:
        write_corpus(args.root)
    skills, tasks, fixtures = load_corpus(args.root)
    verify_checksums(args.root)
    print(f"skills={len(skills)} targets={len(tasks)} reset_fixtures={len(fixtures)}")
    print(f"skills_by_domain={dict(Counter(s.domain.value for s in skills))}")
    print(f"targets_by_domain={dict(Counter(t.domain.value for t in tasks))}")
    print("structural_integrity=PASS sha256=PASS (infrastructure checks only)")


if __name__ == "__main__":
    main()
