import sys
import os
from typing import List


def get_task_text(task: dict) -> str:
    """
    Extract company-identity fields only — we want to reject tasks about the
    exact same prospect, not tasks that share a failure pattern.
    Candidate output is intentionally excluded: all bench-over-commitment tasks
    share phrasing by design, so comparing output text causes false dedup.
    """
    if not isinstance(task, dict):
        return ""
    ctx = task.get("input_context") or {}
    if isinstance(ctx, str):
        try:
            import json as _json
            ctx = _json.loads(ctx)
        except Exception:
            ctx = {}
    brief = (ctx.get("prospect_brief") or {}) if isinstance(ctx, dict) else {}
    if isinstance(brief, str):
        try:
            import json as _json
            brief = _json.loads(brief)
        except Exception:
            brief = {}
    funding = (brief.get("funding") or {}) if isinstance(brief, dict) else {}
    if isinstance(funding, str):
        try:
            import json as _json
            funding = _json.loads(funding)
        except Exception:
            funding = {}
    parts = [
        str(brief.get("company_name", "") if isinstance(brief, dict) else ""),
        str(brief.get("domain", "") if isinstance(brief, dict) else ""),
        str(brief.get("employee_count", "") if isinstance(brief, dict) else ""),
        str(funding.get("amount_usd", "") if isinstance(funding, dict) else ""),
        str(funding.get("closed_at", "") if isinstance(funding, dict) else ""),
    ]
    return " ".join(p for p in parts if p and p not in ("None", "0", "")).lower()


def _ngrams(text: str, n: int = 8) -> set:
    tokens = text.split()
    if not tokens:
        return set()
    return {" ".join(tokens[i : i + n]) for i in range(max(1, len(tokens) - n + 1))}


def _ngram_overlap(a: str, b: str, n: int = 8) -> float:
    """Jaccard-style overlap on word n-grams."""
    ng_a = _ngrams(a, n)
    ng_b = _ngrams(b, n)
    if not ng_a or not ng_b:
        return 0.0
    return len(ng_a & ng_b) / len(ng_a | ng_b)


def embedding_deduplicate(
    new_tasks: List[dict],
    existing_tasks: List[dict],
    threshold: float = 0.85,
) -> List[dict]:
    """
    Filter new_tasks that overlap too heavily with existing_tasks.
    Uses word n-gram Jaccard similarity — no PyTorch required.
    threshold applies to n-gram overlap (default 0.85 mirrors cosine threshold).
    """
    if not new_tasks:
        return new_tasks

    existing_texts = [get_task_text(t) for t in existing_tasks]

    unique: List[dict] = []
    removed = 0
    pool_texts: List[str] = list(existing_texts)

    for t in new_tasks:
        text = get_task_text(t)
        too_similar = any(_ngram_overlap(text, ex, n=6) >= threshold for ex in pool_texts)
        if too_similar:
            removed += 1
        else:
            unique.append(t)
            pool_texts.append(text)

    print(f"  [dedup] removed {removed} / {len(new_tasks)} tasks via n-gram dedup (threshold={threshold})")
    return unique
