"""Create the fixed source-family split before observing experiment outcomes."""

import hashlib
import json
import random
from pathlib import Path

from vigil.benchmark.dataset import load_corpus
from vigil.benchmark.schema import Domain
from vigil.evaluation.prototype_schema import SplitManifest


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    skills, _, _ = load_corpus(root / "benchmark")
    groups: dict[str, list[str]] = {
        name: [] for name in ["fit", "calibration", "validation", "test"]
    }
    rng = random.Random(42)
    for domain in Domain:
        ids = sorted(s.skill_id for s in skills if s.domain == domain)
        rng.shuffle(ids)
        for name, ids_subset in zip(groups, [ids[:3], ids[3:6], ids[6:8], ids[8:]], strict=True):
            groups[name].extend(ids_subset)
    split = SplitManifest.model_validate({"seed": 42, **groups})
    payload = (json.dumps(split.model_dump(), sort_keys=True, indent=2) + "\n").encode("utf-8")
    path = root / "configs/fast_prototype_splits.json"
    if path.exists() and path.read_bytes() != payload:
        raise ValueError("Refusing to change existing split")
    path.write_bytes(payload)
    path.with_suffix(".sha256").write_bytes(
        hashlib.sha256(payload).hexdigest().encode("ascii") + b"\n"
    )
    print("Frozen source-family split: fit=12 calibration=12 validation=8 test=8")


if __name__ == "__main__":
    main()
