"""
Default weights for the 7 context integrity audit dimensions.

All weights must sum to exactly 1.0. 
These can be overridden by passing a custom contract dict to the evaluator 
if an organization wants to prioritize different dimensions.
"""

DEFAULT_CONTRACT: dict[str, float] = {
    "context_staleness": 0.2,
    "retrieval_boundary": 0.20,
    "grounding_fidelity": 0.10,
    "lineage_traceability": 0.15,
    "schema_consistency": 0.15,
    "reproducibility": 0.10,
    "policy_alignment": 0.10,
}

def default_contract()-> dict:
    return dict(DEFAULT_CONTRACT)