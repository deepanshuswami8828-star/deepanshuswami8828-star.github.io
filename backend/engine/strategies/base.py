"""Pluggable strategy framework.

Add a new strategy = subclass Strategy, implement generate_signals(), and put
@register on the class. Nothing else in the platform changes. The engine, the
metrics, the regime tagging and the PDF all pick it up automatically.
"""
from abc import ABC, abstractmethod
import pandas as pd

_REGISTRY: dict[str, type] = {}


def register(cls):
    _REGISTRY[cls.name] = cls
    return cls


def all_strategies() -> dict[str, type]:
    return dict(_REGISTRY)


class Strategy(ABC):
    name: str = "base"
    category: str = "General"
    description: str = ""
    rules_text: str = ""
    params: dict = {}

    # Risk parameters. The ENGINE places stop-loss and target uniformly from
    # these (ATR-based) so every strategy is compared on the same footing.
    atr_period: int = 14
    sl_atr_mult: float = 2.0     # stop distance = sl_atr_mult * ATR at entry
    rr_ratio: float = 2.0        # target distance = rr_ratio * stop distance
    allow_long: bool = True
    allow_short: bool = True

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame aligned to df.index with columns:
            enter_long (bool), enter_short (bool), exit (bool), reason (str)

        Rules:
          * Use ONLY data up to and including each bar (no peeking ahead).
          * The engine fills these at the NEXT bar's open (t -> t+1).
          * 'reason' is the plain-English explanation stored on every trade.
        """
        ...

    @staticmethod
    def _blank(df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {"enter_long": False, "enter_short": False, "exit": False, "reason": ""},
            index=df.index,
        )
