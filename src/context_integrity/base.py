"""
Base class for all audit checks in the Context Integrity Framework.

Any custom check — built-in or user-defined — must inherit from this class
and implement the two required methods: name and audit.

"""
from abc import ABC, abstractmethod
from context_integrity.scoring import Component

class BaseCheck(ABC):
    """
    Abstract base class for all audit checks.
    Every check in the framework (built-in or custom) inherits from this. 
    The evaluator calls audit(row) on each registered check and collects
    the resulting Component for scoring.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this check. Must match the contract key."""
    
    @property
    @abstractmethod
    def default_weight(self) -> float:
        """Default weight for this check in the scoring contract."""
    
    @abstractmethod
    def audit(self, row:dict) -> Component:
        """
        Inspect one interaction row and return a Component.
        row: one dict representing one agent interaction.
        Returns a Component with name, weight, penalty, and detail.
        Never raises: return a Component with penalty=0.3 and an 
        explanatory detail string if the signal is missing or unparseable.
        """
    
    def missing_signal(self, detail: str = "signal missing") -> Component:
        """
        Convenience method for returning a fail-closed missing-signal component.
        USe this instead of returning penalty=0.0 when data is absent.
        """
        return Component(
            name=self.name,
            weight=self.default_weight,
            penalty=0.3,
            detail=detail,
        )