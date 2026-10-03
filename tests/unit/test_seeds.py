import random

import numpy as np
import pytest
import torch

from vigil.utils.seeds import seed_everything


def sample():
    return random.random(), np.random.random(3), torch.rand(3)


def test_all_rngs_reproduce_and_seed_is_logged(caplog):
    with caplog.at_level("INFO"):
        seed_everything(42)
        first = sample()
        seed_everything(42)
        second = sample()
    assert first[0] == second[0]
    np.testing.assert_array_equal(first[1], second[1])
    assert torch.equal(first[2], second[2])
    assert "experiment_seed=42" in caplog.text
    seed_everything(43)
    assert sample()[0] != first[0]


@pytest.mark.parametrize("seed", [-1, 2**32, True, 1.5])
def test_invalid_seeds_rejected(seed):
    with pytest.raises(ValueError):
        seed_everything(seed)
