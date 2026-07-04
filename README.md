# Context Integrity Audit Framework

A governance audit framework for AI agents operating over enterprise data.

Detects staleness, retrieval boundary violations, grounding failures, lineage 
breaks, schema mismatches, reproducibility risks, and policy gaps — scored 
into a single 0–100 integrity score with actionable remediation recommendations.

## Why This Exists

Organizations are deploying AI agents directly over production data — querying 
databases, reading schemas, writing to pipelines, generating reports. There is 
no standard way to audit whether those agents are operating safely with respect 
to data governance, lineage integrity, access compliance, and reproducibility. 
This framework fills that gap.

## Seven Audit Dimensions

| Dimension | What It Checks |
|---|---|
| Context Staleness | Is the retrieved information current? |
| Retrieval Boundary | Did the agent access only authorized data? |
| Grounding Fidelity | Does the output reflect what was retrieved? |
| Lineage Traceability | Can the output be traced back to its source? |
| Schema Consistency | Is the agent using the current schema? |
| Reproducibility | Would the agent produce the same output again? |
| Policy Alignment | Was required data masking applied? |

Each dimension produces a penalty from 0 to 1. A weighted aggregate produces 
a final 0–100 score with a verdict:

- **COMPLIANT** (80–100): agent is operating within governance boundaries
- **REVIEW REQUIRED** (50–79): issues detected, human review recommended
- **NON-COMPLIANT** (0–49): significant violations, output should not be used
- **BLOCKED**: critical violation (e.g. unauthorized PII access), output must 
  be quarantined regardless of overall score

## Scenario Results

| Scenario | Avg Score | Verdict |
|---|---|---|
| Baseline | 96.8 | All COMPLIANT |
| Context Drift | 68.1 | All REVIEW REQUIRED |
| Mixed Failure | 60.6 | REVIEW REQUIRED / NON-COMPLIANT |
| Severe | 44.8 | NON-COMPLIANT + 46 BLOCKED |

## Remediation

Every failing dimension produces a specific, actionable recommendation — not 
just a score. For example:
'''
[RETRIEVAL_BOUNDARY] CRITICAL: Revoke agent access and audit all outputs
from this session. PII data was accessed without authorization.
[SCHEMA_CONSISTENCY] Halt agent queries until schema is synchronized.
Mismatch between agent schema and production schema will produce incorrect
field mappings and query results.
'''

## Install

```bash
pip install context-integrity-audit
```

Development install:

```bash
git clone https://github.com/ritikade2/context-integrity-audit
cd context-integrity-audit
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

Run the bundled offline demo across all four scenarios:

```bash
python3 -m src.context_integrity.cli demo
```

Score your own agent log file (CSV with the required columns):

```bash
python3 -m src.context_integrity.cli run path/to/your_logs.csv
```

Score one example interaction:

```bash
python3 -m src.context_integrity.cli check
```

## Required CSV Columns

To score your own data, your CSV must include these columns:

| Column | Description |
|---|---|
| `source_last_validated` | datetime the source was last verified |
| `source_classification` | PUBLIC / INTERNAL / CONFIDENTIAL / PII |
| `agent_access_level` | PUBLIC / INTERNAL / CONFIDENTIAL |
| `output_claims` | free text of what the agent said |
| `retrieved_content` | free text of what the agent retrieved |
| `query` | the original question or instruction |
| `current_schema_version` | current production schema version |
| `agent_schema_version` | schema version the agent is using |
| `lineage_documented` | True / False |
| `output_matches_source` | float 0.0–1.0 |
| `policy_masking_required` | True / False |
| `policy_masking_applied` | True / False |

## Run Tests

```bash
pytest tests/ -v
```

26 tests, all passing.

## How This Fits Into a Broader Reliability Stack

This framework is the third layer of a three-part reliability stack:

- **Layer 1 — Data Quality**: 
  [AI Operational Data Reliability](https://github.com/ritikade2/ai-operational-data-reliability) 
  — drift detection for AI-generated operational data
- **Layer 2 — Experimentation Integrity**: 
  [Experimentation Integrity Engine](https://github.com/ritikade2/experimentation-integrity-engine) 
  — auditing A/B test reliability before KPI interpretation
- **Layer 3 — Agent Governance**: this framework — auditing context integrity 
  for AI agents operating over enterprise data

## Author

**Ritika De**  
Senior Analytics Engineer | Fractal Analytics  
[github.com/ritikade2](https://github.com/ritikade2)

## License

MIT