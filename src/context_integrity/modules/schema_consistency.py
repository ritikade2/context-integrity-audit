"""
Audit Dimension 5: Schema and Structure Consistency

Checks whether the agent's understanding of the data structure matches
the current production schema. Compares current_schema_version against
agent_schema_version.

Match - no penalty.
Mismatch - full penalty. The agent is operating on a stale or wrong understanding of 
            the data structure.
Missing  -> small precautionary penalty.
"""

from src.context_integrity.scoring import Component

WEIGHT = 0.15


def audit(row: dict) -> Component:
    """
    Compute the schema consistency penalty for one interaction row.
    row: one dictionary from the CSV, representing one agent interaction.
    Returns a Component with the penalty and a short explanation.
    """
    current = row.get("current_schema_version", "").strip()
    agent = row.get("agent_schema_version", "").strip()

    if not current or not agent:
        return Component(
            name="schema_consistency",
            weight=WEIGHT,
            penalty=0.3,
            detail="schema version missing, consistency cannot be verified"
        )
    if current == agent:
        return Component(
            name="schema_consistency",
            weight=WEIGHT,
            penalty=0.0,
            detail=f"schema consistent (both {current})",
        )
    else:
        return Component(
            name="schema_consistency",
            weight=WEIGHT,
            penalty=1.0,
            detail=f"schema mismatch: current={current}, agent using={agent}"
        )