from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


SignalLabel = Literal["BUY", "HOLD", "SELL"]


@dataclass(frozen=True, slots=True)
class SignalRuleConfig:
    """Deterministic score thresholds for BUY/HOLD/SELL classification.

    Thresholds are configuration values, not performance claims. They should be
    validated on chronological validation data before production use.
    """

    sell_threshold: float = 40.0
    buy_threshold: float = 60.0

    def __post_init__(self) -> None:
        for name, value in (
            ("sell_threshold", self.sell_threshold),
            ("buy_threshold", self.buy_threshold),
        ):
            if not 0.0 <= value <= 100.0:
                raise ValueError(f"{name} must be between 0 and 100")
        if self.sell_threshold >= self.buy_threshold:
            raise ValueError("sell_threshold must be lower than buy_threshold")


def classify_signal(
    signal_score: float,
    *,
    config: SignalRuleConfig | None = None,
) -> SignalLabel:
    """Map a 0-100 signal score to BUY/HOLD/SELL deterministically."""
    config = config or SignalRuleConfig()
    score = float(signal_score)
    if not np.isfinite(score):
        raise ValueError("signal_score must be finite")
    if not 0.0 <= score <= 100.0:
        raise ValueError("signal_score must be between 0 and 100")

    if score >= config.buy_threshold:
        return "BUY"
    if score <= config.sell_threshold:
        return "SELL"
    return "HOLD"
