"""
Context Integrity Audit Framework

A governance audit framework for AI agents operating over enterprise data.
Detects staleness, retrieval boundary violations, grounding failures,
lineage breaks, schema mismatches, reproducibility risks, and policy gaps.

Author: Ritika De
"""

from src.context_integrity.evaluator import evaluate_row, evaluate_file
from src.context_integrity.remediation import get_recommendations
from src.context_integrity.scoring import IntegrityScore, Component, Verdict

__version__ = "0.1.0"
__author__ = "Ritika De"

__all__ = [
    "evaluate_row",
    "evaluate_file",
    "get_recommendations",
    "IntegrityScore",
    "Component",
    "Verdict",
    "__version__",
    "__author__",
]