"""Public-data Capital Behavior Engine.

The package infers price-pressure states from observable market data. It does
not identify market participants or assert institutional order flow.
"""

from .evidence import build_capital_evidence
from .intraday import build_intraday_capital_assessment
from .scoring import build_capital_assessment
from .state import CapitalState, transition_state
from .outcomes import label_future_outcomes, outcome_is_complete

__all__ = [
    "CapitalState",
    "build_capital_assessment",
    "build_capital_evidence",
    "build_intraday_capital_assessment",
    "transition_state",
    "label_future_outcomes",
    "outcome_is_complete",
]
