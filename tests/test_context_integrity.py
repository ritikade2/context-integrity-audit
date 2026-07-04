"""
Tests for the Context Integrity Audit Framework.
Run with: pytest tests/
"""

import pytest
from src.context_integrity.scoring import score_components, Component, Verdict
from src.context_integrity.contract import default_contract
from src.context_integrity.evaluator import evaluate_row, evaluate_file
from src.context_integrity.remediation import get_recommendations
from src.context_integrity.modules.context_staleness import audit as stale_audit, REFERENCE_DATE
from src.context_integrity.modules.retrieval_boundary import audit as boundary_audit
from src.context_integrity.modules.grounding_fidelity import audit as grounding_audit
from src.context_integrity.modules.lineage_traceability import audit as lineage_audit
from src.context_integrity.modules.schema_consistency import audit as schema_audit
from src.context_integrity.modules.reproducibility import audit as repro_audit
from src.context_integrity.modules.policy_alignment import audit as policy_audit


# Shared test rows
CLEAN_ROW = {
    "source_last_validated": "2026-06-20 12:00:00",
    "source_classification": "INTERNAL",
    "agent_access_level": "INTERNAL",
    "output_claims": "Total Q1 revenue was 4.2M across all regions.",
    "retrieved_content": "Q1 revenue totaled 4.2 million dollars across all regions.",
    "query": "What is the total revenue for Q1?",
    "current_schema_version": "v4",
    "agent_schema_version": "v4",
    "lineage_documented": "True",
    "output_matches_source": "0.95",
    "policy_masking_required": "False",
    "policy_masking_applied": "False",
}

VIOLATED_ROW = {
    "source_last_validated": "2026-06-01 12:00:00",
    "source_classification": "PII",
    "agent_access_level": "INTERNAL",
    "output_claims": "Customer John Smith has account balance of $45,231.",
    "retrieved_content": "Account balance data is available for authorized users only.",
    "query": "What is the account balance for customer 8821?",
    "current_schema_version": "v4",
    "agent_schema_version": "v2",
    "lineage_documented": "False",
    "output_matches_source": "0.3",
    "policy_masking_required": "True",
    "policy_masking_applied": "False",
}


# Scoring spine 
def test_perfect_score():
    result = score_components([
        Component("a", 0.5, 0.0),
        Component("b", 0.5, 0.0),
    ])
    assert result.score == 100.0
    assert result.verdict == Verdict.COMPLIANT


def test_total_failure():
    result = score_components([
        Component("a", 0.5, 1.0),
        Component("b", 0.5, 1.0),
    ])
    assert result.score == 0.0
    assert result.verdict == Verdict.NON_COMPLIANT


def test_forced_block():
    result = score_components(
        [Component("a", 1.0, 0.0)],
        forced_block=True,
    )
    assert result.verdict == Verdict.BLOCKED


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError):
        score_components([
            Component("a", 0.6, 0.0),
            Component("b", 0.6, 0.0),
        ])


def test_empty_components_raises():
    with pytest.raises(ValueError):
        score_components([])


# Contract
def test_contract_sums_to_one():
    c = default_contract()
    assert abs(sum(c.values()) - 1.0) < 1e-9


def test_contract_has_seven_dimensions():
    c = default_contract()
    assert len(c) == 7

def test_custom_contract_actually_applies():
    # Put all weight on retrieval_boundary which has a penalty in VIOLATED_ROW.
    # If custom contract works, score should be much lower than default.
    custom = {
        "context_staleness": 0.0001,
        "retrieval_boundary": 0.9993,
        "grounding_fidelity": 0.0001,
        "lineage_traceability": 0.0001,
        "schema_consistency": 0.0001,
        "reproducibility": 0.0001,
        "policy_alignment": 0.0002,
    }
    result_custom = evaluate_row(VIOLATED_ROW, contract=custom)
    result_default = evaluate_row(VIOLATED_ROW)
    # Custom contract forces almost all weight onto the failing dimension
    assert result_custom.score != result_default.score

# Individual modules 
def test_context_staleness_fresh():
    row = {"source_last_validated": "2026-06-20 12:00:00"}
    result = stale_audit(row, now=REFERENCE_DATE)
    assert result.penalty == 0.0


def test_context_staleness_stale():
    row = {"source_last_validated": "2026-06-01 12:00:00"}
    result = stale_audit(row, now=REFERENCE_DATE)
    assert result.penalty == 1.0


def test_retrieval_boundary_authorized():
    row = {"source_classification": "INTERNAL", "agent_access_level": "INTERNAL"}
    component, blocked = boundary_audit(row)
    assert component.penalty == 0.0
    assert blocked is False


def test_retrieval_boundary_pii_violation():
    row = {"source_classification": "PII", "agent_access_level": "INTERNAL"}
    component, blocked = boundary_audit(row)
    assert component.penalty == 1.0
    assert blocked is True


def test_grounding_fidelity_well_grounded():
    row = {
        "output_claims": "Revenue was 4.2 million dollars.",
        "retrieved_content": "Q1 revenue totaled 4.2 million dollars across all regions.",
        "query": "What is the revenue?",
    }
    result = grounding_audit(row)
    assert result.penalty < 0.5


def test_grounding_fidelity_missing_content():
    row = {"output_claims": "", "retrieved_content": "", "query": ""}
    result = grounding_audit(row)
    assert result.penalty == 0.3
    assert "missing" in result.detail


def test_lineage_documented():
    assert lineage_audit({"lineage_documented": "True"}).penalty == 0.0
    assert lineage_audit({"lineage_documented": "False"}).penalty == 1.0

def test_lineage_missing_value():
    result = lineage_audit({"lineage_documented": None})
    assert result.penalty == 0.3
    assert "missing" in result.detail

def test_schema_consistent():
    row = {"current_schema_version": "v4", "agent_schema_version": "v4"}
    assert schema_audit(row).penalty == 0.0


def test_schema_mismatch():
    row = {"current_schema_version": "v4", "agent_schema_version": "v2"}
    assert schema_audit(row).penalty == 1.0


def test_reproducibility_high_match():
    assert repro_audit({"output_matches_source": "0.95"}).penalty <= 0.1


def test_policy_violation():
    row = {"policy_masking_required": "True", "policy_masking_applied": "False"}
    assert policy_audit(row).penalty == 1.0


def test_policy_compliant():
    row = {"policy_masking_required": "True", "policy_masking_applied": "True"}
    assert policy_audit(row).penalty == 0.0


# evaluator end to end
def test_clean_row_is_compliant():
    result = evaluate_row(CLEAN_ROW, now=REFERENCE_DATE)
    assert result.verdict == Verdict.COMPLIANT
    assert result.score >= 80.0

def test_violated_row_is_blocked():
    result = evaluate_row(VIOLATED_ROW, now=REFERENCE_DATE)
    assert result.verdict == Verdict.BLOCKED


# Scenario files
def test_baseline_all_compliant():
    result = evaluate_file("data/synthetic_logs/scenario_baseline.csv", now=REFERENCE_DATE)
    assert result["verdict_counts"]["COMPLIANT"] == 200
    assert result["blocked_count"] == 0


def test_scores_decrease_across_scenarios():
    baseline = evaluate_file("data/synthetic_logs/scenario_baseline.csv", now=REFERENCE_DATE)
    drift = evaluate_file("data/synthetic_logs/scenario_context_drift.csv", now=REFERENCE_DATE)
    mixed = evaluate_file("data/synthetic_logs/scenario_mixed_failure.csv", now=REFERENCE_DATE)
    severe = evaluate_file("data/synthetic_logs/scenario_severe.csv", now=REFERENCE_DATE)
    assert baseline["average_score"] > drift["average_score"]
    assert drift["average_score"] > mixed["average_score"]
    assert mixed["average_score"] > severe["average_score"]


def test_severe_has_blocked():
    result = evaluate_file("data/synthetic_logs/scenario_severe.csv", now=REFERENCE_DATE)
    assert result["blocked_count"] > 0
    assert result["average_score"] < 60.0


# Remediation 
def test_clean_row_no_remediation():
    result = evaluate_row(CLEAN_ROW)
    recs = get_recommendations(result)
    assert not any("CRITICAL" in r for r in recs)
    assert not any("BLOCKED" in r for r in recs)
    assert not any("RETRIEVAL_BOUNDARY" in r for r in recs)


def test_violated_row_has_remediation():
    result = evaluate_row(VIOLATED_ROW)
    recs = get_recommendations(result)
    assert len(recs) > 1
    assert any("RETRIEVAL_BOUNDARY" in r for r in recs)