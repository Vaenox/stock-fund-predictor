from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimeSeriesFold:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


def build_walk_forward_splits(
    n_samples: int,
    *,
    n_splits: int = 3,
    test_size: int | None = None,
    gap: int = 5,
) -> tuple[TimeSeriesFold, ...]:
    """Create expanding-window walk-forward folds with a leakage gap."""
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    if n_splits <= 0:
        raise ValueError("n_splits must be positive")
    if gap < 0:
        raise ValueError("gap cannot be negative")

    if test_size is None:
        test_size = max(1, n_samples // (n_splits + 1))
    if test_size <= 0:
        raise ValueError("test_size must be positive")

    minimum = n_splits * test_size + gap
    if n_samples <= minimum:
        raise ValueError(
            "not enough samples for requested walk-forward configuration"
        )

    first_test_start = n_samples - n_splits * test_size
    folds: list[TimeSeriesFold] = []
    for fold_index in range(n_splits):
        test_start = first_test_start + fold_index * test_size
        test_end = test_start + test_size
        train_end = test_start - gap
        if train_end <= 0:
            raise ValueError("walk-forward fold has no training observations")
        folds.append(
            TimeSeriesFold(
                train_start=0,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
    return tuple(folds)
