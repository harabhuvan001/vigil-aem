"""Central seed setup; no claim of cross-platform bitwise determinism."""

import logging
import random

import numpy as np
import torch


def seed_everything(seed: int) -> int:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32 - 1:
        raise ValueError("Seed must be an integer in [0, 2**32 - 1]")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    logging.getLogger(__name__).info("experiment_seed=%d", seed)
    return seed
