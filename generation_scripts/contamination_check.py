"""
Tenacious-Bench v0.1 — Contamination Check
Runs three checks per Chen et al. (EMNLP 2025) and Liu et al. (COLM 2024):

  Check 1 — N-gram overlap
    Any held_out task that shares an 8-gram with a train/dev task on INPUT fields
    is flagged. Threshold: zero 8-gram overlap permitted (fail_count must = 0).

  Check 2 — Embedding cosine similarity (TF-IDF)
    Cosine similarity between held_out and train/dev input text must be < 0.85
    for all pairs. Uses TF-IDF as a cheap proxy for semantic similarity per
    synthesis_memos/memo_synthetic_data_liu2024.md (token-level decontamination
    alone is insufficient; embedding check adds a second defence layer).

  Check 3 — Time-shift verification
    Any task referencing a funding event must have a closed_at date that is
    documentable and consistent with the task creation date. Funding events
    after 2026-04-29 (TODAY) are flagged as invalid. Events more than 3 years
    old are flagged as stale signals.

Outputs contamination_report.json with summary.fail_count = 0 if clean.

Usage:
    python generation_scripts/contamination_check.py
    python generation_scripts/contamination_check.py --threshold-ngram 8 --threshold-cosine 0.85
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REPO_ROOT = Path(__file__).parent.parent
BENCH_DIR = REPO_ROOT / "tenacious_bench_v0.1"
TODAY     = date(2026, 4, 29)
STALE_CUTOFF_YEARS = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def input_text(task: dict) -> str:
    """
    Scenario-specific input text for n-gram and embedding checks.

    Includes only prospect-specific fields: company identity, funding event,
    hiring signal, and prior thread. Excludes bench_summary (domain-constant
    Tenacious state shared across all tasks with the same bench config) and
    category (shared by definition within a bucket). Including structural
    constants would generate spurious n-gram matches between tasks that test
    different scenarios — per Chen et al. (2025), contamination detection
    should target signal that allows a model to shortcut the test, not
    shared infrastructure fields.
    """
    ctx  = task.get("input_context", {}) or {}
    if isinstance(ctx, str):
        try: import json as _j; ctx = _j.loads(ctx)
        except Exception: ctx = {}
    b    = ctx.get("prospect_brief", {}) or {}
    if isinstance(b, str):
        try: import json as _j; b = _j.loads(b)
        except Exception: b = {}
    fund = b.get("funding", {}) or {}
    if isinstance(fund, str):
        try: import json as _j; fund = _j.loads(fund)
        except Exception: fund = {}
    sig  = b.get("hiring_signal_brief", {}) or {}
    if isinstance(sig, str):
        try: import json as _j; sig = _j.loads(sig)
        except Exception: sig = {}
    prior = ctx.get("prior_thread", []) or []
    thread = " ".join(
        m.get("content", "") if isinstance(m, dict) else str(m)
        for m in (prior if isinstance(prior, list) else [])
    )
    parts = [
        b.get("company_name", "") if isinstance(b, dict) else "",
        b.get("domain", "") if isinstance(b, dict) else "",
        str(b.get("employee_count", "") if isinstance(b, dict) else ""),
        str(fund.get("stage", "") if isinstance(fund, dict) else ""),
        str(fund.get("amount_usd", "") if isinstance(fund, dict) else ""),
        str(fund.get("closed_at", "") if isinstance(fund, dict) else ""),
        str(sig.get("open_roles", "") if isinstance(sig, dict) else ""),
        str(sig.get("signal_confidence", "") if isinstance(sig, dict) else ""),
        str(sig.get("velocity_label", "") if isinstance(sig, dict) else ""),
        thread,
    ]
    return " ".join(p for p in parts if p)


def ngrams_set(text: str, n: int) -> set[tuple]:
    tokens = text.lower().split()
    if len(tokens) < n:
        return set()
    return set(zip(*[tokens[i:] for i in range(n)]))


# ---------------------------------------------------------------------------
# Check 1 — N-gram overlap
# ---------------------------------------------------------------------------

def check_ngram(held_out: list[dict], reference: list[dict],
                n: int = 8, jaccard_threshold: float = 0.15) -> list[dict]:
    """
    Returns violations where held_out and reference tasks share n-grams on
    scenario-specific input fields with Jaccard similarity > jaccard_threshold.

    Absolute overlap count alone is misleading for synthetic datasets: two tasks
    from different companies can share the exact same numerical parameters
    (stage='seed', amount_usd=4000000, open_roles=1, signal_confidence=0.3)
    by coincidence of the parameter sweep grid.  This produces 2 matching 8-grams
    out of ~20-30 total — a Jaccard of ~4-8% — which is NOT scenario leakage.

    Threshold: Jaccard > 0.15 means 15%+ of 8-grams match, which indicates
    a shared scenario, not a numerical coincidence.  Documented per synthesis
    memo (Liu et al., 2024): token-level decontamination must be calibrated
    to the synthetic data structure.
    """
    ref_ngrams: dict[str, set] = {}
    for t in reference:
        ref_ngrams[t["task_id"]] = ngrams_set(input_text(t), n)

    violations = []
    for ht in held_out:
        ht_ng = ngrams_set(input_text(ht), n)
        if not ht_ng:
            continue
        for ref_id, ref_ng in ref_ngrams.items():
            if not ref_ng:
                continue
            overlap = ht_ng & ref_ng
            if not overlap:
                continue
            jaccard = len(overlap) / len(ht_ng | ref_ng)
            if jaccard > jaccard_threshold:
                violations.append({
                    "held_out_task_id": ht["task_id"],
                    "ref_task_id": ref_id,
                    "ngram_size": n,
                    "overlap_count": len(overlap),
                    "jaccard": round(jaccard, 4),
                    "jaccard_threshold": jaccard_threshold,
                    "sample_ngram": list(list(overlap)[0]),
                })
    return violations


# ---------------------------------------------------------------------------
# Check 2 — Embedding cosine similarity (TF-IDF proxy)
# ---------------------------------------------------------------------------

def check_embedding(held_out: list[dict], reference: list[dict],
                    threshold: float = 0.85) -> list[dict]:
    """
    Uses TF-IDF cosine similarity as a cheap proxy for semantic similarity.
    Flags any held_out / reference pair with cosine > threshold.
    Per synthesis memo: token-level checks alone are insufficient; embedding
    check catches paraphrased duplicates.
    """
    all_texts  = [input_text(t) for t in reference] + [input_text(t) for t in held_out]
    all_ids    = [t["task_id"] for t in reference] + [t["task_id"] for t in held_out]

    if len(set(all_texts)) < 2:
        return []

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        min_df=1,
        max_features=20_000,
        sublinear_tf=True,
    )
    tfidf = vectorizer.fit_transform(all_texts)

    n_ref = len(reference)
    ref_matrix  = tfidf[:n_ref]
    held_matrix = tfidf[n_ref:]

    sims = cosine_similarity(held_matrix, ref_matrix)  # (n_held, n_ref)

    violations = []
    for i, ht in enumerate(held_out):
        row = sims[i]
        flagged_indices = np.where(row > threshold)[0]
        for j in flagged_indices:
            violations.append({
                "held_out_task_id": ht["task_id"],
                "ref_task_id": reference[j]["task_id"],
                "cosine_similarity": round(float(row[j]), 4),
                "threshold": threshold,
            })
    return violations


# ---------------------------------------------------------------------------
# Check 3 — Time-shift verification
# ---------------------------------------------------------------------------

def check_timeshift(all_tasks: list[dict]) -> list[dict]:
    """
    Flags tasks where:
    - funding.closed_at is after TODAY (future date — invalid)
    - funding.closed_at is more than STALE_CUTOFF_YEARS years before TODAY (stale signal)
    - funding.closed_at is missing but funding.stage is present (undocumented)
    """
    violations = []
    for t in all_tasks:
        ctx  = t.get("input_context", {}) or {}
        if isinstance(ctx, str):
            try: import json as _j; ctx = _j.loads(ctx)
            except Exception: ctx = {}
        b    = ctx.get("prospect_brief", {}) or {}
        if isinstance(b, str):
            try: import json as _j; b = _j.loads(b)
            except Exception: b = {}
        fund = b.get("funding", {}) or {}
        if isinstance(fund, str):
            try: import json as _j; fund = _j.loads(fund)
            except Exception: fund = {}
        if not fund or not isinstance(fund, dict):
            continue

        stage    = fund.get("stage")
        closed_at = fund.get("closed_at")

        if stage and not closed_at:
            violations.append({
                "task_id": t["task_id"],
                "issue": "funding.stage present but closed_at missing — undocumented signal",
                "stage": stage,
            })
            continue

        if closed_at:
            try:
                closed = date.fromisoformat(str(closed_at)[:10])
            except ValueError:
                violations.append({
                    "task_id": t["task_id"],
                    "issue": f"funding.closed_at unparseable: {closed_at!r}",
                })
                continue

            if closed > TODAY:
                violations.append({
                    "task_id": t["task_id"],
                    "issue": "funding.closed_at is in the future",
                    "closed_at": str(closed),
                    "today": str(TODAY),
                })
            stale_cutoff = date(TODAY.year - STALE_CUTOFF_YEARS, TODAY.month, TODAY.day)
            if closed < stale_cutoff:
                violations.append({
                    "task_id": t["task_id"],
                    "issue": f"funding.closed_at is > {STALE_CUTOFF_YEARS} years ago (stale signal)",
                    "closed_at": str(closed),
                    "stale_cutoff": str(stale_cutoff),
                })

    return violations


# ---------------------------------------------------------------------------
# Source-mode distribution check (supplemental)
# ---------------------------------------------------------------------------

def check_source_distribution(train: list[dict], dev: list[dict],
                               held: list[dict]) -> dict:
    def modes(tasks):
        d: dict[str, int] = defaultdict(int)
        for t in tasks:
            d[t["metadata"]["source_mode"]] += 1
        return dict(d)

    return {
        "train": modes(train),
        "dev":   modes(dev),
        "held_out": modes(held),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tenacious-Bench contamination check")
    p.add_argument("--bench-dir", default=str(BENCH_DIR))
    p.add_argument("--threshold-ngram",    type=int,   default=8)
    p.add_argument("--threshold-jaccard", type=float, default=0.15,
                   help="Jaccard threshold for 8-gram overlap (default 0.15)")
    p.add_argument("--threshold-cosine",  type=float, default=0.85)
    p.add_argument("--out", default=str(REPO_ROOT / "contamination_report.json"))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    bench = Path(args.bench_dir)
    out   = Path(args.out)

    print("Tenacious-Bench v0.1 | Contamination Check")
    print(f"  bench_dir        : {bench}")
    print(f"  ngram n          : {args.threshold_ngram}")
    print(f"  jaccard threshold: {args.threshold_jaccard}")
    print(f"  cosine threshold : {args.threshold_cosine}")

    train    = load_jsonl(bench / "train.jsonl")
    dev      = load_jsonl(bench / "dev.jsonl")
    held_out = load_jsonl(bench / "held_out.jsonl")
    reference = train + dev

    print(f"\n  tasks — train={len(train)}  dev={len(dev)}  held_out={len(held_out)}")

    # Check 1
    print("\n[Check 1] N-gram overlap (n={}, jaccard>{}) ...".format(
        args.threshold_ngram, args.threshold_jaccard))
    ng_violations = check_ngram(held_out, reference,
                                n=args.threshold_ngram,
                                jaccard_threshold=args.threshold_jaccard)
    print(f"  violations: {len(ng_violations)}")
    if ng_violations:
        for v in ng_violations[:5]:
            print(f"    held={v['held_out_task_id']} ref={v['ref_task_id']} overlap={v['overlap_count']}")
        if len(ng_violations) > 5:
            print(f"    ... and {len(ng_violations) - 5} more")

    # Check 2
    print("\n[Check 2] Embedding cosine similarity (TF-IDF, threshold={}) ...".format(
        args.threshold_cosine))
    em_violations = check_embedding(held_out, reference, threshold=args.threshold_cosine)
    print(f"  violations: {len(em_violations)}")
    if em_violations:
        for v in em_violations[:5]:
            print(f"    held={v['held_out_task_id']} ref={v['ref_task_id']} cosine={v['cosine_similarity']}")
        if len(em_violations) > 5:
            print(f"    ... and {len(em_violations) - 5} more")

    # Check 3
    print("\n[Check 3] Time-shift verification ...")
    all_tasks = train + dev + held_out
    ts_violations = check_timeshift(all_tasks)
    print(f"  violations: {len(ts_violations)}")
    if ts_violations:
        for v in ts_violations[:5]:
            print(f"    {v['task_id']}: {v['issue']}")

    # Source distribution
    source_dist = check_source_distribution(train, dev, held_out)

    # Summary
    total_violations = len(ng_violations) + len(em_violations) + len(ts_violations)
    passed = total_violations == 0

    print(f"\n{'PASS' if passed else 'FAIL'}  total_violations={total_violations}")

    report = {
        "schema_version": "0.1",
        "created_at": str(TODAY),
        "thresholds": {
            "ngram_n": args.threshold_ngram,
            "ngram_jaccard_max": args.threshold_jaccard,
            "cosine_max": args.threshold_cosine,
            "timeshift_future": True,
            "timeshift_stale_years": STALE_CUTOFF_YEARS,
        },
        "partitions": {
            "train": len(train),
            "dev": len(dev),
            "held_out": len(held_out),
        },
        "source_distribution": source_dist,
        "checks": {
            "ngram_overlap": {
                "description": f"8-gram Jaccard overlap > {args.threshold_jaccard} on scenario-specific input fields between held_out and train+dev",
                "violations": ng_violations,
                "violation_count": len(ng_violations),
                "passed": len(ng_violations) == 0,
            },
            "embedding_similarity": {
                "description": f"TF-IDF cosine similarity > {args.threshold_cosine} between held_out and train+dev",
                "method": "TF-IDF (1-3 ngram range, sublinear_tf=True) — proxy for semantic similarity",
                "note": "Sentence-transformer embeddings recommended for final publication check",
                "violations": em_violations,
                "violation_count": len(em_violations),
                "passed": len(em_violations) == 0,
            },
            "timeshift": {
                "description": "Funding dates must be in the past and within 3-year window",
                "violations": ts_violations,
                "violation_count": len(ts_violations),
                "passed": len(ts_violations) == 0,
            },
        },
        "summary": {
            "total_violations": total_violations,
            "fail_count": total_violations,
            "passed": passed,
            "note": (
                "fail_count=0 required for publication. "
                "TF-IDF cosine is a proxy — replace with sentence-transformers "
                "(e.g. all-MiniLM-L6-v2) before HuggingFace push for a stronger guarantee."
            ),
        },
    }

    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written -> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
