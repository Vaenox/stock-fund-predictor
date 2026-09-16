from __future__ import annotations

import pytest

from app.ml.splitting import build_walk_forward_splits


def test_walk_forward_splits_are_ordered_and_have_gap():
    folds = build_walk_forward_splits(100, n_splits=3, test_size=10, gap=5)

    assert len(folds) == 3
    previous_test_end = 0
    for fold in folds:
        assert fold.train_start == 0
        assert fold.train_end <= fold.test_start
        assert fold.test_start - fold.train_end == 5
        assert fold.test_end - fold.test_start == 10
        assert fold.test_start >= previous_test_end
        previous_test_end = fold.test_end


def test_walk_forward_rejects_insufficient_samples():
    with pytest.raises(ValueError, match="not enough samples"):
        build_walk_forward_splits(20, n_splits=3, test_size=5, gap=5)
