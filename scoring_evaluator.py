"""
Tenacious-Bench v0.1 — Pipeline A scoring evaluator.
Source: technical_specification.md §5.1 + Tenacious Style Guide v2.

Scoring steps:
  1. Hard gates — banned phrases, external-'bench' word, bench capacity, funding
     stage mismatch.  Any failure → composite = 0, evaluation stops.
  2. LLM-as-judge (Claude Sonnet 4.6) scores each of the five rubric dimensions 1–5.
     Falls back to deterministic heuristics when ANTHROPIC_API_KEY is absent or
     --no-llm is passed.
  3. Weighted composite = Σ(dimension_score × weight).
     Pass: composite ≥ pass_threshold (default 3.5) AND zero hard-gate failures.

Usage:
    python scoring_evaluator.py                           # schema.json, all tasks
    python scoring_evaluator.py tasks.jsonl               # JSONL partition file
    python scoring_evaluator.py schema.json --task TEN-BOC-001
    python scoring_evaluator.py schema.json --no-llm      # deterministic only
    python scoring_evaluator.py schema.json --seed 42 --output results_seed42.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Banned phrase list — Tenacious Style Guide v2 (banned_phrases table + tone markers)
# ---------------------------------------------------------------------------
GLOBAL_BANNED_PHRASES: list[str] = [
    # Offshore-vendor quality clichés
    "world-class",
    "top talent",
    "a-players",
    "rockstar",
    "ninja",
    "wizard",
    # Hype / growth promises
    "skyrocket",
    "supercharge",
    "game-changer",
    "game-changing",
    "disruptor",
    "paradigm shift",
    # Filler openers
    "i hope this email finds you well",
    "hope this finds you well",
    "just wanted to reach out",
    "just following up",
    "circling back",
    # "Quick" formulations (subject and body)
    "quick question",
    "quick chat",
    # Consultant jargon
    "synergize",
    "synergy",
    "leverage",
    "ecosystem",
    # Fake urgency / guilt
    "don't miss out",
    "you'll regret",
    "per my last email",
    "per my last",
    # Sycophantic / sycophantic openers
    "would love to",
    "excited to share",
    # Self-centred boasting
    "years of experience",
    # Cost / arbitrage framing (tone-drift category)
    "cost arbitrage",
    "cost savings",
    "dramatically reduce",
    "cost reduction",
    # Misc style-guide violations
    "amazing opportunity",
    "as you may know",
    "best in class",
]

# Bench capacity from data_needed/tenacious_sales_data/seed/bench_summary.json
BENCH_CAPACITY: dict[str, int] = {
    "python": 7,
    "go": 3,
    "data": 9,
    "ml": 5,
    "infra": 4,
    "rust": 0,
}

# Funding stage aliases for mismatch detection
STAGE_ALIASES: dict[str, list[str]] = {
    "seed": [],
    "series_a": ["series a", "series-a"],
    "series_b": ["series b", "series-b"],
    "series_c": ["series c", "series-c"],
    "series_d": ["series d", "series-d"],
}

CALENDAR_PATTERNS: list[str] = [
    "cal.com/",
    "calendly.com/",
    "gettenacious.com/",
    "book here",
    "schedule a call",
    "book a call",
    "https://cal.",
    "pick a time",
]

VAGUE_QUANTITY_PHRASES: list[str] = [
    "several engineers",
    "a few engineers",
    "many engineers",
    "some engineers",
]


# ---------------------------------------------------------------------------
# Hard gates  (Pipeline A — Step 1)
# ---------------------------------------------------------------------------

def check_hard_gates(task: dict, output: str) -> tuple[bool, list[str]]:
    """
    Returns (all_passed, violations).
    Any non-empty violations list → composite_score = 0.
    """
    violations: list[str] = []
    out = output.lower()

    # 1. Global banned phrases (tone_adherence / Professional marker)
    for phrase in GLOBAL_BANNED_PHRASES:
        if phrase in out:
            violations.append(f"global_banned_phrase: '{phrase}'")

    # 2. External "bench" word (Style Guide v2 — Professional marker)
    #    "bench" must not appear in prospect-facing messages.
    #    Use "engineering team", "available capacity", "engineers ready to deploy".
    if re.search(r"\bbench\b(?!mark)", out):
        violations.append(
            "external_bench_word: 'bench' used in prospect-facing message "
            "(style_guide_v2: replace with 'engineering team' or 'available capacity')"
        )

    # 3. Task-specific banned phrases (ground_truth.banned_phrases)
    gt = task.get("ground_truth", {})
    for phrase in gt.get("banned_phrases", []):
        if phrase.lower() in out:
            violations.append(f"task_banned_phrase: '{phrase}'")

    # 4. Funding stage mismatch (signal_grounding hard gate)
    brief = task.get("input_context", {}).get("prospect_brief", {})
    funding = brief.get("funding", {})
    if funding:
        actual_stage = funding.get("stage", "").lower()
        for stage, aliases in STAGE_ALIASES.items():
            if stage != actual_stage:
                for alias in aliases:
                    if alias in out:
                        violations.append(
                            f"funding_stage_mismatch: output contains '{alias}' "
                            f"but brief stage is '{actual_stage}'"
                        )

    # 5. Bench capacity — zero-available stacks (bench_honesty hard gate)
    bench = task.get("input_context", {}).get("bench_summary", {})
    for stack, info in bench.items():
        available = (
            info.get("available_engineers", 0)
            if isinstance(info, dict)
            else int(info)
        )
        if available == 0:
            commitment_patterns = [
                rf"\bhave {stack}\b",
                rf"{stack} engineer",
                rf"deploy.*{stack}",
                rf"{stack}.*available",
                rf"get.*{stack}.*started",
                rf"{stack}.*ready",
            ]
            for pat in commitment_patterns:
                if re.search(pat, out):
                    violations.append(
                        f"bench_over_commitment: commits '{stack}' stack (available_engineers=0)"
                    )
                    break

    return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Deterministic heuristic scoring  (fallback when no LLM)
# ---------------------------------------------------------------------------

def _count_words(text: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", text).split())


def _has_calendar_link(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in CALENDAR_PATTERNS)


def score_dimensions_deterministic(task: dict, output: str) -> dict[str, int]:
    """
    Heuristic 1-5 scores per dimension.
    icp_accuracy defaults to 3 — cannot be reliably inferred from string checks alone.
    Scores are conservative; the LLM judge is the authoritative scorer.
    """
    out = output.lower()
    gt = task.get("ground_truth", {})
    rubric = task.get("evaluator_config", {}).get("rubric", [])
    scores: dict[str, int] = {}

    for dim in rubric:
        d = dim["dimension"]

        if d == "tone_adherence":
            banned_hit = (
                any(p in out for p in GLOBAL_BANNED_PHRASES)
                or bool(re.search(r"\bbench\b(?!mark)", out))
                or any(p.lower() in out for p in gt.get("banned_phrases", []))
            )
            max_words = gt.get("max_word_count")
            word_count = _count_words(output)
            over = max_words and word_count > max_words
            if banned_hit:
                scores[d] = 1
            elif over and word_count > max_words * 1.3:
                scores[d] = 2
            elif over:
                scores[d] = 3
            else:
                scores[d] = 4

        elif d == "signal_grounding":
            required = gt.get("required_phrases", [])
            if not required:
                scores[d] = 3
            else:
                found = sum(1 for p in required if p.lower() in out)
                ratio = found / len(required)
                scores[d] = (
                    5 if ratio >= 0.8 else
                    3 if ratio >= 0.4 else
                    2 if ratio > 0 else
                    1
                )

        elif d == "bench_honesty":
            vague_hit = any(p in out for p in VAGUE_QUANTITY_PHRASES)
            scores[d] = 2 if vague_hit else 4

        elif d == "icp_accuracy":
            scores[d] = 3  # requires semantic understanding; deferred to LLM judge

        elif d == "completeness":
            require_cal = gt.get("require_calendar_link", False)
            has_cal = _has_calendar_link(output)
            if require_cal and not has_cal:
                scores[d] = 1
            elif require_cal and has_cal:
                scores[d] = 4
            else:
                scores[d] = 3

        else:
            scores[d] = 3

    return scores


# ---------------------------------------------------------------------------
# LLM judge  (Pipeline A — Step 2, primary path)
# ---------------------------------------------------------------------------

def score_dimensions_llm(task: dict, output: str) -> tuple[dict[str, int], str]:
    """
    Returns (dimension_scores, method).
    method is 'llm' on success, 'deterministic' on fallback.
    """
    try:
        import anthropic
    except ImportError:
        print("  [warn] anthropic not installed — deterministic fallback", file=sys.stderr)
        return score_dimensions_deterministic(task, output), "deterministic"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  [warn] ANTHROPIC_API_KEY not set — deterministic fallback", file=sys.stderr)
        return score_dimensions_deterministic(task, output), "deterministic"

    client = anthropic.Anthropic(api_key=api_key)
    rubric = task.get("evaluator_config", {}).get("rubric", [])

    prompt = f"""You are a Tenacious sales evaluation judge. Score the agent output on each rubric dimension 1–5.

INPUT CONTEXT:
{json.dumps(task.get("input_context", {}), indent=2)}

GROUND TRUTH:
{json.dumps(task.get("ground_truth", {}), indent=2)}

AGENT OUTPUT:
{output}

RUBRIC (score each dimension 1–5):
{json.dumps(rubric, indent=2)}

SCORING ANCHORS (all dimensions):
1 = Fails entirely — violation immediately visible to a CTO/VP reader
2 = Partially fails — violation present but partially mitigated
3 = Borderline — satisfies minimum; a careful reader would flag weaknesses
4 = Passes clearly — only minor non-material imperfections
5 = Exemplary — matches a labeled GOOD example in Tenacious Style Guide v2

KEY RULES FROM TENACIOUS STYLE GUIDE v2:
- "bench" must NOT appear externally; use "engineering team" or "available capacity"
- signal_confidence < 0.6 → interrogative/conditional language only ("are you finding…", "if you're scoping…")
- signal_confidence ≥ 0.6 → assertive language permitted
- Cold outreach body ≤ 120 words; warm reply ≤ 200 words; re-engagement ≤ 100 words
- One ask per message; no stacking
- Signature: First name, title, "Tenacious Intelligence Corporation", gettenacious.com — nothing else
- Competitor gaps framed as research questions, never as prospect failures
- Capacity commitments must not exceed bench_summary available_engineers per stack

Return ONLY a JSON object with integer scores 1–5:
{{"tone_adherence": int, "signal_grounding": int, "bench_honesty": int, "icp_accuracy": int, "completeness": int}}
No markdown. No explanation."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("```").strip()
        scores = {k: int(v) for k, v in json.loads(raw).items()}
        return scores, "llm"
    except Exception as exc:
        print(f"  [warn] LLM judge failed ({exc}) — deterministic fallback", file=sys.stderr)
        return score_dimensions_deterministic(task, output), "deterministic"


# ---------------------------------------------------------------------------
# Pipeline A entry point
# ---------------------------------------------------------------------------

def score_task(task: dict, use_llm: bool = True) -> dict:
    output = task.get("candidate_output", "")
    rubric = task.get("evaluator_config", {}).get("rubric", [])
    pass_threshold = task.get("pass_threshold", 3.5)
    meta = task.get("metadata", {})
    category = meta.get("category", task.get("category", ""))
    difficulty = meta.get("difficulty", task.get("difficulty", ""))

    # Step 1 — hard gates
    gates_passed, violations = check_hard_gates(task, output)
    if not gates_passed:
        return {
            "task_id": task["task_id"],
            "category": category,
            "difficulty": difficulty,
            "composite_score": 0.0,
            "pass_threshold": pass_threshold,
            "passed": False,
            "hard_gate_failures": violations,
            "dimension_scores": {},
            "scored_by": "hard_gate",
            "expected_pass": task.get("expected_pass"),
        }

    # Step 2 — dimension scoring (LLM or deterministic)
    if use_llm:
        dimension_scores, scored_by = score_dimensions_llm(task, output)
    else:
        dimension_scores = score_dimensions_deterministic(task, output)
        scored_by = "deterministic"

    # Step 3 — weighted composite (1–5 scale)
    composite = round(
        sum(dimension_scores.get(d["dimension"], 3) * d["weight"] for d in rubric),
        4,
    )

    return {
        "task_id": task["task_id"],
        "category": category,
        "difficulty": difficulty,
        "composite_score": composite,
        "pass_threshold": pass_threshold,
        "passed": composite >= pass_threshold,
        "hard_gate_failures": [],
        "dimension_scores": dimension_scores,
        "scored_by": scored_by,
        "expected_pass": task.get("expected_pass"),
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_result(result: dict) -> None:
    status = "PASS" if result["passed"] else "FAIL"
    expected = result.get("expected_pass")
    match_tag = ""
    if expected is not None:
        match_tag = " [correct]" if result["passed"] == expected else " [UNEXPECTED]"

    print(
        f"\n[{status}]{match_tag}  {result['task_id']}"
        f"  ({result['category']}, {result['difficulty']})"
        f"  composite {result['composite_score']:.2f}/{result['pass_threshold']}"
        f"  [{result['scored_by']}]"
    )
    if result["hard_gate_failures"]:
        for v in result["hard_gate_failures"]:
            print(f"  GATE  {v}")
    else:
        for dim, score in result["dimension_scores"].items():
            bar = "#" * score + "." * (5 - score)
            icon = "OK" if score >= 4 else ("--" if score == 3 else "!!")
            print(f"  {icon}  {dim:<22}  {bar}  {score}/5")


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_tasks(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        if path.suffix == ".jsonl":
            return [json.loads(line) for line in f if line.strip()]
        data = json.load(f)
    if "tasks" in data:
        return data["tasks"]
    if "task_id" in data:
        return [data]
    return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Tenacious-Bench v0.1 Pipeline A evaluator")
    p.add_argument("schema", nargs="?", default="schema.json",
                   help="Path to schema.json or a .jsonl partition file")
    p.add_argument("--task", help="Score a single task by task_id")
    p.add_argument("--no-llm", action="store_true",
                   help="Deterministic scoring only (no Anthropic API call)")
    p.add_argument("--seed", type=int, default=42,
                   help="RNG seed — logged in JSON output; required for final submission")
    p.add_argument("--output", help="Write JSON results to this file")
    return p


def main() -> int:
    args = build_parser().parse_args()

    path = Path(args.schema)
    if not path.exists():
        path = Path(__file__).parent / args.schema
    if not path.exists():
        print(f"Error: not found: {args.schema}", file=sys.stderr)
        return 2

    tasks = load_tasks(path)
    if not tasks:
        print("Error: no tasks found", file=sys.stderr)
        return 2

    if args.task:
        tasks = [t for t in tasks if t.get("task_id") == args.task]
        if not tasks:
            print(f"Error: task_id '{args.task}' not found", file=sys.stderr)
            return 2

    use_llm = not args.no_llm
    scorer_label = "llm (claude-sonnet-4-6)" if use_llm else "deterministic"
    print(
        f"Tenacious-Bench v0.1  |  {len(tasks)} task(s)"
        f"  |  seed={args.seed}  |  scorer={scorer_label}"
    )

    results = [score_task(t, use_llm=use_llm) for t in tasks]
    for r in results:
        print_result(r)

    n_pass = sum(1 for r in results if r["passed"])
    unexpected = [
        r for r in results
        if r.get("expected_pass") is not None and r["passed"] != r["expected_pass"]
    ]
    print(f"\nSummary: {n_pass}/{len(results)} pass", end="")
    if unexpected:
        print(
            f"  |  {len(unexpected)} unexpected: {[r['task_id'] for r in unexpected]}",
            end="",
        )
    print()

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(
            json.dumps({"seed": args.seed, "results": results}, indent=2),
            encoding="utf-8",
        )
        print(f"Results written to {out_path}")

    return 0 if not unexpected else 1


if __name__ == "__main__":
    sys.exit(main())
