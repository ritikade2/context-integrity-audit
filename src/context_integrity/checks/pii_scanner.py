"""
PII Scanner Check - a worked example of an independent grounded check.
This check scans the raw text of output_claims for PII patterns using regex.
It does NOT trust the policy_masking_applied field - it independently detects 
whether PII appears in the output regardless of what the caller says.
This is the canonical example of how to write a custom check that plugs into 
the Context Integrity Audit Framework. Copy this file, rename the class, and 
implement your own audit() logic to add a new dimension.

Detect:
- Email addresses
- US phone numbers
- US Social security numbers
- Credit card number (basic pattern)
- Name + account number patterns
"""

import re
from context_integrity.base import BaseCheck
from context_integrity.scoring import Component

# PII patterns — compiled once at module load for efficiency
_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "name_account": re.compile(
        r"\b(customer|client|user|account\s+holder)\s+\w+\s+\w*"
        r"(account|balance|ssn|id|number)[:\s#]*\d+",
        re.IGNORECASE,
    ),
}

class PIIScannerCheck(BaseCheck):
    """
    Independently scans output_claims for PII pattterns.
    Unlike policy_alignment (which trusts the enterprise system's self-reported metadata),
    this check reads the raw output text and detects PII directly. Penalty scales with the 
    number of distinct PII types found, saturating at 1.0 when 3 or mroe types are detected.
    """

    @property 
    def name(self) -> str:
        return "pii_scanner"
    
    @property
    def default_weight(self) -> float:
        return 0.15
    
    def audit(self, row:dict) -> Component:
        """
        Scan output_claims for PII pattersn and return a penalty.
        Penalty:
        - 0 PII types found: 0.0 (clean)
        - 1 PII type found: 0.4 (warning)
        - 2 PII types found: 0.7 (significant)
        - 3+ PII types found: 1.0 (critical)
        """
        output = str(row.get("output_claims") or "").strip()
        if not output:
            return self.missing_signal(
                "output_claims missing, PII scan not possible"
            )
        found_types = []
        for label, pattern in _PATTERNS.items():
            if pattern.search(output):
                found_types.append(label)
        
        count = len(found_types)

        if count == 0:
            return Component(
                name=self.name,
                weight=self.default_weight,
                penalty=0.0,
                detail="no PII patterns detected in output"
            )
        elif count == 1:
            penalty = 0.4
        elif count ==2 :
            penalty = 0.7
        else:
            penalty = 1.0
        
        detail = f"PII detected in output: {', '.join(found_types)}"
        return Component(
            name=self.name,
            weight=self.default_weight,
            penalty=penalty,
            detail=detail,
        )