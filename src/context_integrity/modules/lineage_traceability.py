"""
Audit Dimension 4: Lineage Traceability

Checks whether the agent's output can be traced back to a documented
source. 
Reads the lineage_documented column (True/False).

True - lineage is intact, no penalty.
False - lineage is broken, full penalty.
Missing - cannot determine, small precautionary penalty applied.
"""

from src.context_integrity.scoring import Component

WEIGHT = 0.15

def audit(row: dict) -> Component:
    """
    Component the lineage traceability penalty for one interaction row.
    row: one dictionary from the CSV, representing one agent interaction.
    Returns a Component with the penalty and a short explanation.
    """
    raw = row.get("lineage_documented", None)
    #Handle both boolean True/False and string "True"/"False" from the CSV
    if isinstance(raw, bool):
        lineage_ok = raw
    elif isinstance(raw, str):
        lineage_ok = raw.strip().lower() == "true"
    else:
        #Missing value, apply small precautionary penalty
        return Component(
            name="lineage_traceability",
            weight=WEIGHT,
            penaty=0.3,
            detail="lineage_documented missing, tracebility unknown",
        )
    
    if lineage_ok:
        return Component(
            name="lineage_traceability",
            weight=WEIGHT,
            penalty=0.0,
            detail="lineage documented and traceable"
        )
    else:
        return Component(
            name="lineage_traceability",
            weight=WEIGHT,
            penalty=1.0,
            detail="lineage not documented, output cannot be traced to source"
        )
    