# Contributing to the Context Integrity Audit Framework

## Adding a Custom Check

The framework is designed to be extended. Adding a new audit dimension takes
three steps and does not require touching any existing code.

### Step 1 — Create your check file

Create a new file in `src/context_integrity/checks/`. Name it after your
dimension, e.g. `retention_policy.py`.

Your check must inherit from `BaseCheck` and implement three things:

```python
from context_integrity.base import BaseCheck
from context_integrity.scoring import Component

class RetentionPolicyCheck(BaseCheck):

    @property
    def name(self) -> str:
        return "retention_policy"  # must be unique across all checks

    @property
    def default_weight(self) -> float:
        return 0.10  # your check's share of the score (0.0 to 1.0)

    def audit(self, row: dict) -> Component:
        # read from the row dict and compute a penalty in [0, 1]
        # 0.0 = no problem, 1.0 = total failure
        value = row.get("your_column")

        if value is None:
            return self.missing_signal("your_column missing")

        penalty = 0.0  # your logic here

        return Component(
            name=self.name,
            weight=self.default_weight,
            penalty=penalty,
            detail="explanation of the penalty",
        )
```

**Rules your check must follow:**

- Never raise an exception — return `self.missing_signal(...)` if data is absent
- Penalty must always be in `[0.0, 1.0]`
- `name` must be unique and not conflict with the seven built-in dimensions
- Do not trust self-reported metadata blindly — compute from raw text where possible

### Step 2 — Pass your check to the evaluator

```python
from context_integrity.evaluator import evaluate_row
from context_integrity.checks.retention_policy import RetentionPolicyCheck

result = evaluate_row(row, extra_checks=[RetentionPolicyCheck()])
```

The evaluator automatically renormalizes all weights to sum to 1.0. Your
check's `default_weight` is taken as its share, and the seven built-in
dimensions are scaled down proportionally.

### Step 3 — Add a test

Add a test to `tests/test_context_integrity.py`:

```python
def test_retention_policy_check():
    from context_integrity.checks.retention_policy import RetentionPolicyCheck
    check = RetentionPolicyCheck()
    row = {"your_column": "some value that should fail"}
    result = check.audit(row)
    assert result.penalty > 0.0
    assert "your_column" in result.detail
```

Run `pytest tests/ -v` to confirm.

---

## Built-in Audit Dimensions

| Name | File | What It Checks |
|---|---|---|
| `context_staleness` | `modules/context_staleness.py` | Source freshness |
| `retrieval_boundary` | `modules/retrieval_boundary.py` | Access authorization |
| `grounding_fidelity` | `modules/grounding_fidelity.py` | Output vs retrieved text |
| `lineage_traceability` | `modules/lineage_traceability.py` | Output traceability |
| `schema_consistency` | `modules/schema_consistency.py` | Schema version match |
| `reproducibility` | `modules/reproducibility.py` | Output consistency |
| `policy_alignment` | `modules/policy_alignment.py` | Masking compliance |

The PII scanner (`checks/pii_scanner.py`) is a worked example of a custom
check that independently verifies real truth from raw text, rather than
trusting self-reported metadata.

---

## Adding a Column to the Input Schema

If your check needs a new column that does not exist in the default schema,
add it to your CSV and document it here. The evaluator passes the full row
dict to every check — any column you add is automatically available.

Document new columns in your check's docstring and in the README's
"Required CSV Columns" section.

---

## Code Style

- stdlib only for check logic — no heavyweight ML dependencies
- Fail closed — missing signals return `self.missing_signal()`, not `penalty=0.0`
- One file per check
- All checks must have at least one pytest test

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

All 31 tests must pass before submitting a pull request.