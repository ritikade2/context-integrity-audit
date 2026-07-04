"""
Shared scoring engine for Context Integrity Audit Framework. 
This is only to turn a list of weighted panelties into a fnal 0-100 score, 
a verdict label, and a readable report.
Every audit module in this project will produce a "Component"
and hand it to this file.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Verdict(str, Enum):
    """ The final label attached to a score.""" 
    COMPLIANT = "COMPLIANT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NON_COMPLIANT = "NON_COMPLIANT"
    BLOCKED = "BLOCKED"

@dataclass(frozen = True)
class Component:
    """
    One audit dimension's contribution to the final score.
    name: short label, e.g. "context_staleness"
    weight: how much this dimension counts toward the total (all weights across all components must add up to 1.0)
    penalty: how badly this dimension failed, from 0.0 to 1.0 
    detail: a short human-readable explanation of why this penalty was given.
    """
    name: str
    weight: float
    penalty: float
    detail: str = ""

@dataclass(frozen = True)
class IntegrityScore:
    """The final score: a number, a verdict, and a full breakdown."""
    score: float
    verdict: Verdict
    components: tuple[Component, ...]

    def report(self) -> str:
        """Return a readable multi-line summary."""
        lines = [f"score: {self.score}  verdict: {self.verdict.value}"]
        for c in self.components:
            line = f"  - {c.name}: weight={c.weight} penalty={c.penalty}"
            if c.detail:
                line += f" ({c.detail})"
            lines.append(line)
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Return this result as a plain dictionary (useful for saving as JSON)."""
        return {
            "score": self.score,
            "verdict": self.verdict.value,
            "components": [
                {
                    "name": c.name,
                    "weight": c.weight,
                    "penalty": c.penalty,
                    "detail": c.detail,
                }
                for c in self.components
            ],
        }

# Score bands: at or above 80 = COMPLIANT, at or above 50 = REVIEW_REQUIRED, anything below that = NON_COMPLIANT. 

DEFAULT_BANDS: tuple[tuple[float, Verdict], ...] = (
    (80.0, Verdict.COMPLIANT),
    (50.0, Verdict.REVIEW_REQUIRED),
    (0.0, Verdict.NON_COMPLIANT),
)

def _verdict_for(score: float, bands) -> Verdict:
    """Pick the correct verdict label for a given score."""
    for threshold, verdict in sorted(bands, key=lambda b:b[0], reverse=True):
        if score >= threshold:
            return verdict
    return bands[-1][1]  # default to the lowest band if something goes wrong

def score_components(
        components: list[Component],
        *,
        forced_block: bool = False,
        block_reason: str = "",
) -> IntegrityScore:
    """
    Turn a list of components into final IntegrityScore.
    forced_block: set this to True when a hard-floor rule has been broken
        (for example, an agent accessed data it was never authorized to see).
        When True, the verdict is forced to BLOCKED regardless of the score.
    block_reason: a short explanation shown when forced_block is True.
    """

    if not components:
        raise ValueError("at least one component is required to score")
    
    #Safety checks: every weight and penalty must be a valid number.
    for c in components:
        if not 0.0 <= c.weight <= 1.0:
            raise ValueError(f"{c.name}: weight must be between 0 and 1, got {c.weight}")
        if not 0.0 <= c.penalty <= 1.0:
            raise ValueError(f"{c.name}: penalty must be between 0 and 1, got {c.penalty}")

    total_weight = sum(c.weight for c in components)
    if abs(total_weight - 1.0) > 1e-9:
        raise ValueError(f"component weights must sum to 1.0, got {total_weight:.4f}")

    weighted_penalty = sum(c.weight * c.penalty for c in components)
    score = max(0.0, min(100.0, 100.0 * (1.0 - weighted_penalty)))
    score = round(score, 1)

    if forced_block:
        #Still report the true score to see how close it was, but
        # the verdict overrides to BLOCKED.
        return IntegrityScore(
            score=score,
            verdict=Verdict.BLOCKED,
            components=tuple(components),
        )
    
    verdict = _verdict_for(score, DEFAULT_BANDS)
    return IntegrityScore(score=score, verdict=verdict, components=tuple(components))
