"""Paired source-family statistics for deterministic finite-corpus outcomes."""

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import binomtest


def paired_statistics(
    frame: pd.DataFrame, *, seed: int, bootstrap: int, permutations: int
) -> dict[str, Any]:
    # Equal family sizes in this benchmark; cluster means weight families equally.
    family_effects = frame.groupby("source_skill_id")["reward_difference"].mean().to_numpy()
    rng = np.random.default_rng(seed)
    samples = rng.choice(family_effects, size=(bootstrap, len(family_effects)), replace=True).mean(
        axis=1
    )
    effect = float(family_effects.mean())
    null = (rng.choice([-1, 1], size=(permutations, len(family_effects))) * family_effects).mean(
        axis=1
    )
    p_value = float((1 + (np.abs(null) >= abs(effect)).sum()) / (permutations + 1))
    lost = int(((frame.success_without == 1) & (frame.success_with == 0)).sum())
    gained = int(((frame.success_without == 0) & (frame.success_with == 1)).sum())
    discordant = lost + gained
    return {
        "mean_reward_effect": effect,
        "bootstrap_95_ci": [float(v) for v in np.quantile(samples, [0.025, 0.975])],
        "cluster_count": len(family_effects),
        "task_count": len(frame),
        "paired_cluster_permutation_p": p_value,
        "mcnemar_discordant_losses": lost,
        "mcnemar_discordant_gains": gained,
        "mcnemar_exact_p": float(binomtest(gained, discordant, 0.5).pvalue) if discordant else None,
        "interpretation": "Exploratory synthetic-family variation; deterministic single runs. "
        "Task-level McNemar ignores within-family dependence; do not use as population proof.",
    }
