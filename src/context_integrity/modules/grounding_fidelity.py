"""
Audit Dimension 3: Grounding Fidelity

Checks whether the agent's output claims are actually supported by the
retrieved source material. Computes grounding directly from text using
four deterministic statistical signals:

1. unknown_word_rate  -- fraction of output words absent from retrieved content
2. numeric_inconsistency -- fraction of numbers in output absent from source
3. verbosity_ratio -- output length relative to source, saturating at 2x
4. question_echo -- fraction of query words echoed back in the output

Each signal returns a severity in [0, 1]. The four are averaged into a
final penalty. A low penalty means the output is well grounded in the
retrieved context. A high penalty means the output diverges significantly
from what was retrieved -- a signal of hallucination or fabrication.
"""
import re
from src.context_integrity.scoring import Component

WEIGHT = 0.10

_WORD = re.compile(r"[a-z0-9]+")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_STOPWORDS = frozenset(
    "a an the and or but of to in on at for by with from as is are was were be "
    "been being it its this that these those who whom what when where why how "
    "which while do does did has have had will would can could should i you he "
    "she they we them his her their our your my me".split()
)

def _content_words(text: str) -> set:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS}

def _unknown_word_rate(output: str, source: str) -> float:
    """Fraction of output content words absent from the retrieved source."""
    output_words = _content_words(output)
    if not output_words:
        return 0.0
    unsupported = output_words - _content_words(source)
    return len(unsupported) / len(output_words)

def _numeric_inconsistency(output: str, source: str) -> float:
    """Fraction of numbers in the output not present in the source."""
    output_nums = set(_NUMBER.findall(output))
    if not output_nums:
        return 0.0
    unsupported = output_nums - set(_NUMBER.findall(source))
    return len(unsupported) / len(output_nums)

def _verbosity_ratio(output: str, source: str) -> float:
    """Output length relative to source, saturing at 2x."""
    output_len = len(_WORD.findall(output.lower()))
    source_len = len(_WORD.findall(source.lower()))
    if output_len == 0 or source_len == 0:
        return 0.0
    return min(1.0, (output_len / source_len) / 2.0)

def _question_echo(output: str, query: str) -> float:
    """Fraction of query content words echoed back in the output."""
    if not query or not query.strip():
        return 0.0
    query_words = _content_words(query)
    if not query_words:
        return 0.0
    echoed = query_words & _content_words(output)
    return len(echoed) / len(query_words)

def audit(row: dict) -> Component:
    """
    Compute grounding fidelity penalty for one interaction row.
    Reads output_claims, retrieved_content, and query columns.
    Returns a Component with the averaged signal penalty and explanation.
    """

    output = str(row.get("output_claims") or "").strip()
    source = str(row.get("retrieved_content") or "").strip()
    query = str(row.get("query") or "").strip()

    if not output or not source:
        return Component(
            name="grounding_fidelity",
            weight=WEIGHT,
            penalty=0.0,
            detail="output_claims or retrieved_content missing, grounding not measured",
        )
    s1 = _unknown_word_rate(output, source)
    s2 = _numeric_inconsistency(output, source)
    s3 = _verbosity_ratio(output, source)
    s4 = _question_echo(output, query)

    penalty = round((s1 + s2 + s3 + s4) / 4.0, 4)
    penalty = min(1.0, penalty)

    if penalty <= 0.1:
        detail = f"well grounded (grounding penalty {penalty:.2f})"
    elif penalty <= 0.4:
        detail = f"partial grounding gap (grounding penalty {penalty:.2f})"
    else:
        detail = f"significant grounding failure (grounding penalty {penalty:.2f})"

    return Component(
        name="grounding_fidelity",
        weight=WEIGHT,
        penalty=penalty,
        detail=detail,
    )