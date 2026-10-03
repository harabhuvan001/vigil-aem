import math

import pytest

from vigil.evaluation.metrics import TransferLabel, classify_transfer, transfer_delta


@pytest.mark.parametrize(
    "with_reward,without_reward,expected", [(1, -1, 2), (0, 0, 0), (-1, 1, -2)]
)
def test_delta_direction(with_reward, without_reward, expected):
    assert transfer_delta(with_reward, without_reward) == expected


@pytest.mark.parametrize(
    "delta,expected",
    [
        (0.11, TransferLabel.HELP),
        (-0.11, TransferLabel.HARM),
        (0, TransferLabel.NEUTRAL),
        (0.1, TransferLabel.NEUTRAL),
        (-0.1, TransferLabel.NEUTRAL),
    ],
)
def test_explicit_threshold_boundaries(delta, expected):
    assert classify_transfer(delta, epsilon=0.1) == expected


def test_nonfinite_values_and_negative_threshold_are_rejected():
    with pytest.raises(ValueError):
        transfer_delta(math.inf, 0)
    with pytest.raises(ValueError):
        classify_transfer(0, epsilon=-1)
    with pytest.raises(ValueError):
        classify_transfer(math.nan, epsilon=0.1)
