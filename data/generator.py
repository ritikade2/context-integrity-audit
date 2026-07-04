"""
Synthetic enterprise agent interaction log generator.

Produces four CSV files, one per audit scenario, into data/synthetic_logs/.
Each row is one agent interaction. The 7 audit modules read these columns
to compute their penalties.

This generates 4 scenario files, directly in: python3 data/generator.py
"""

import csv
import os
import random
from datetime import datetime, timedelta

random.seed(42) # makes results reproducible.

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "synthetic_logs")

COLUMNS = [
    "interaction_id",
    "agent_id",
    "query",
    "retrieved_sources",
    "retrieved_content",
    "source_last_validated", # datetime
    "current_schema_version", # v1, v2
    "agent_schema_version", # what agent things the schema is
    "output_claims", # free text: what agent said
    "source_classification", #PUBLIC, INTERNAL, CONFIDENTIAL, PII
    "agent_access_level", # PUBLIC, INTERNAL, CONFIDENTIAL
    "lineage_documented", # True/False
    "output_matches_source", # float 0.0-1.0
    "policy_masking_required", # True/False
    "policy_masking_applied", # True/False
]

NOW = datetime(2026, 6, 21, 12, 0, 0) 

QUERIES = [
    "What is the total revenue for Q1?",
    "List all active customers in the northeast region.",
    "Summarize the top 5 product categories by margin.",
    "How many support tickets were resolved last week?",
    "What is the average order value for premium accounts?",
    "Show churn rate by segment for the last 90 days.",
    "What percentage of leads converted in March?",
    "List agents with more than 10 escalations this month.",
]

SOURCES = [
    "sales_db.revenue_summary",
    "crm.customer_master",
    "product_db.category_margins",
    "support_db.ticket_log",
    "orders_db.account_summary",
    "analytics.churn_metrics",
    "crm.lead_funnel",
    "support_db.agent_performance",
]

OUTPUT_CLAIMS = [
    "Total Q1 revenue was $4.2M across all regions.",
    "Found 1,847 active customers in the northeast.",
    "Top category is Electronics with 34% margin.",
    "312 tickets were resolved last week.",
    "Average order value for premium accounts is $890.",
    "Overall churn rate is 3.2% with enterprise segment at 1.1%.",
    "Lead conversion rate in March was 18.4%.",
    "7 agents exceeded 10 escalations this month.",
]

RETRIEVED_CONTENT = [
    "Q1 revenue totaled 4.2 million dollars across all regions. Northeast contributed 1.1M, Southwest 0.9M, and remaining regions 2.2M.",
    "Active customer count in northeast region is 1847. Accounts flagged inactive in last 90 days: 203.",
    "Top product category by margin is Electronics at 34 percent. Second is Apparel at 28 percent. Third is Home Goods at 22 percent.",
    "Support tickets resolved in the last 7 days: 312. Open tickets: 87. Average resolution time: 4.2 hours.",
    "Premium account average order value is 890 dollars. Standard account average is 340 dollars. Total premium accounts: 4201.",
    "Overall churn rate for last 90 days is 3.2 percent. Enterprise segment churn is 1.1 percent. SMB segment churn is 6.8 percent.",
    "Lead conversion rate for March was 18.4 percent. Total leads: 2340. Converted: 430. Average time to convert: 12 days.",
    "Agents with more than 10 escalations this month: 7. Highest escalation count: 23. Department with most escalations: billing.",
]

def _timestamp(days_ago: float) -> str: 
    # Return a timestamp string for N days before NOW
    return(NOW - timedelta(days = days_ago)).strftime("%Y-%m-%d %H:%M:%S")

def _row(
        i: int,
        *, 
        days_stale: float = 0.5,
        schema_match: bool = True,
        classification: str = "INTERNAL",
        access_level: str = "INTERNAL",
        lineage: bool = True,
        match_score: float = 0.95,
        masking_required: bool = False,
        masking_applied: bool = False,
) -> dict:
    """Builds a single interaction row with the given parameters."""
    idx = i % len(QUERIES)
    return {
        "interaction_id": f"INT-{i:04d}",
        "agent_id": f"agent-{(i % 3) + 1:02d}",
        "query": QUERIES[idx],
        "retrieved_sources": SOURCES[idx],
        "retrieved_content": RETRIEVED_CONTENT[idx],
        "source_last_validated": _timestamp(days_stale),
        "current_schema_version": "v4",
        "agent_schema_version": "v4" if schema_match else "v2",
        "output_claims": OUTPUT_CLAIMS[idx],
        "source_classification": classification,
        "agent_access_level": access_level,
        "lineage_documented": lineage,
        "output_matches_source": round(match_score, 2),
        "policy_masking_required": masking_required,
        "policy_masking_applied": masking_applied,
    }

def generate_baseline(n: int = 200) -> list[dict]:
    """
    Scenario 1: everything is working correctly.
    Sources are fresh, schema matches, access is authorized,
    lineage is documented, outputs match source, masking is applied where needed.
    """
    rows = []
    for i in range(n):
        masking_req = random.random() < 0.15
        rows.append(_row(
            i,
            days_stale=random.uniform(0.1, 1.5), # less than 2 days old
            schema_match=True,
            classification = "INTERNAL",
            access_level = "INTERNAL",
            lineage = True,
            match_score = random.uniform(0.88, 1.0),
            masking_required = masking_req,
            masking_applied = masking_req,
        ))
    return rows

def generate_context_drift(n: int = 200) -> list[dict]:
    """
    Scenario 2: context staleness and schema mismatch introduced.
    Sources are significantly out of date, and the agent is using an old
    schema version. Access and lineage are still fine.
    """
    rows = []
    for i in range(n):
        masking_req = random.random() < 0.15
        rows.append(_row(
            i,
            days_stale=random.uniform(10.0, 30.0), #10 to 30 days old
            schema_match=random.random() < 0.6, #60% of rows have schema mismatch
            classification = "INTERNAL",
            access_level = "INTERNAL",
            lineage = True,
            match_score = random.uniform(0.65, 0.90), #slightly degraded grounding
            masking_required = masking_req,
            masking_applied = masking_req,
        ))
    return rows

def generate_mixed_failure(n: int = 200) -> list[dict]:
    """
    Scenario 3: multiple dimensions failing at moderate severity.
    Staleness, schema mismatches, lineage gaps, and grounding failures
    all present but no single catastrophic event like a PII access violation.
    """
    rows = []
    for i in range(n):
        masking_req = random.random() < 0.25
        rows.append(_row(
            i,
            days_stale = random.uniform(5.0, 20.0), # 5 to 20 days old
            schema_match = random.random() < 0.5, # 50% of rows have schema mismatch
            classification = "INTERNAL",
            access_level = "INTERNAL",
            lineage = random.random() > 0.35, # 35% of rows missing lineage
            match_score = random.uniform(0.5, 0.85), # degraded grounding
            masking_required = masking_req,
            masking_applied=masking_req if random.random() > 0.3 else False,
        ))
    return rows

def generate_severe(n: int = 200) -> list[dict]:
    """
    Scenario 4: critical violations that should trigger BLOCKED verdict.
    Agent is accessing PII and CONFIDENTIAL data it is not authorized to see.
    Grounding failures and lineage breaks also present.
    """
    rows = []
    classifications = ["PII", "CONFIDENTIAL", "INTERNAL", "INTERNAL"]
    for i in range(n):
        classification = random.choice(classifications)
        rows.append(_row(
            i,
            days_stale = random.uniform(8.0, 25.0), # 8 to 25 days old
            schema_match = random.random() > 0.5, 
            classification = classification,
            access_level = "INTERNAL", # agent is never authorized for PII 
            lineage = random.random() > 0.5, # 50% of rows missing lineage
            match_score = random.uniform(0.3, 0.65), # degraded grounding
            masking_required = classification in ["PII", "CONFIDENTIAL"],
            masking_applied = False, # masking not applied in this scenario
        ))
    return rows

def write_scenario(name: str, rows: list[dict]) -> None:
    """Write a list of rows to a CSV file in data/synthetic_logs."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"scenario_{name}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows -> {path}")

if __name__ == "__main__":
    write_scenario("baseline", generate_baseline())
    write_scenario("context_drift", generate_context_drift())
    write_scenario("mixed_failure", generate_mixed_failure())
    write_scenario("severe", generate_severe())
    print("done. all 4 scenario files generated.")