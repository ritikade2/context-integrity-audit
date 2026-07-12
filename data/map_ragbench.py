"""
Maps RAGBench subsets (cuad, finqa) to the Context Integrity Audit Framework
14-column schema and saves them as CSV files in data/synthetic_logs/.

Usage:
    python3 data/map_ragbench.py
    
Outputs:
    data/synthetic_logs/ragbench_cuad.csv
    data/synthetic_logs/ragbench_finqa.csv
"""

import csv
import os
from datasets import load_dataset

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "synthetic_logs")

COLUMNS = [
    "interaction_id",
    "agent_id",
    "query",
    "retrieved_sources",
    "retrieved_content",
    "source_last_validated",
    "current_schema_version",
    "agent_schema_version",
    "output_claims",
    "source_classification",
    "agent_access_level",
    "lineage_documented",
    "output_matches_source",
    "policy_masking_required",
    "policy_masking_applied",
]

# Domain-specific governance metadata
DOMAIN_CONFIG = {
    "cuad": {
        "source_classification": "CONFIDENTIAL",
        "agent_access_level": "INTERNAL",
        "source_last_validated": "2024-01-01 00:00:00",
        "current_schema_version": "v1",
        "agent_schema_version": "v1",
        "policy_masking_required": False,
        "policy_masking_applied": False,
    },
    "finqa": {
        "source_classification": "INTERNAL",
        "agent_access_level": "INTERNAL",
        "source_last_validated": "2024-01-01 00:00:00",
        "current_schema_version": "v1",
        "agent_schema_version": "v1",
        "policy_masking_required": False,
        "policy_masking_applied": False,
    },
}


def map_row(row: dict, idx: int, subset: str, config: dict) -> dict:
    """Map one RAGBench row to the framework's 14-column schema."""

    # retrieved_content: join all documents into one string
    docs = row.get("documents") or []
    if isinstance(docs, list):
        retrieved_content = " ".join(str(d) for d in docs)[:2000]
    else:
        retrieved_content = str(docs)[:2000]

    # lineage: True when the agent actually cited specific sentences
    utilized = row.get("all_utilized_sentence_keys") or []
    lineage_documented = len(utilized) > 0

    # output_matches_source: use ragas_faithfulness as proxy
    # fall back to adherence_score if faithfulness is None
    faithfulness = row.get("ragas_faithfulness")
    if faithfulness is not None:
        output_matches_source = round(float(faithfulness), 4)
    else:
        output_matches_source = 1.0 if row.get("adherence_score") else 0.3

    return {
        "interaction_id": f"{subset.upper()}-{idx:05d}",
        "agent_id": row.get("generation_model_name", "unknown")[:30],
        "query": str(row.get("question", ""))[:500],
        "retrieved_sources": f"ragbench.{subset}",
        "retrieved_content": retrieved_content,
        "source_last_validated": config["source_last_validated"],
        "current_schema_version": config["current_schema_version"],
        "agent_schema_version": config["agent_schema_version"],
        "output_claims": str(row.get("response", ""))[:500],
        "source_classification": config["source_classification"],
        "agent_access_level": config["agent_access_level"],
        "lineage_documented": lineage_documented,
        "output_matches_source": output_matches_source,
        "policy_masking_required": config["policy_masking_required"],
        "policy_masking_applied": config["policy_masking_applied"],
    }


def convert_subset(subset: str, split: str = "test") -> None:
    """Download, map, and save one RAGBench subset."""
    print(f"loading ragbench/{subset} ({split} split)...")
    ds = load_dataset("rungalileo/ragbench", subset, split=split)
    config = DOMAIN_CONFIG[subset]

    rows = [map_row(row, idx, subset, config) for idx, row in enumerate(ds)]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"ragbench_{subset}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows -> {path}")


if __name__ == "__main__":
    convert_subset("cuad", split="train+validation+test")
    convert_subset("finqa", split="train+validation+test")
    print("done.")