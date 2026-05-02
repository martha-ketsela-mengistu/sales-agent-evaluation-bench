"""
build_training_data.py

Constructs Path B (ORPO/SimPO) preference pairs from tenacious_bench_v0.1/train.jsonl.

Every train task has expected_pass=False — the candidate_output is the rejected side.
This script generates a passing (chosen) rewrite for each task via gpt-4o-mini
(openai family), then formats the pairs for TRL ORPOTrainer / CPOTrainer.

Preference-leakage prevention (Li et al. 2025): the to-be-trained backbone is
Qwen 3.5.  Chosen rewrites must NOT come from a Qwen-family model.  gpt-4o-mini
is the designated rewriter per router_config.json.

Usage:
    python generation_scripts/build_training_data.py          # all 139 train tasks
    python generation_scripts/build_training_data.py --dry-run  # no API calls, stub output
    python generation_scripts/build_training_data.py --limit 10  # first N tasks only

Output:
    training_data/orpo_pairs.jsonl      — TRL-compatible preference pairs
    training_data/generation_report.json — per-task status, cost, retry counts
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
TRAIN_FILE = ROOT / "tenacious_bench_v0.1" / "train.jsonl"
HELD_OUT_FILE = ROOT / "tenacious_bench_v0.1" / "held_out.jsonl"
OUTPUT_DIR = ROOT / "training_data"
PAIRS_FILE = OUTPUT_DIR / "orpo_pairs.jsonl"
REPORT_FILE = OUTPUT_DIR / "generation_report.json"
ROUTER_CONFIG = Path(__file__).parent / "router_config.json"

sys.path.insert(0, str(Path(__file__).parent))
from cost_tracker import log_cost, get_running_total, BudgetExceededError
from pipeline_logger import stage_start, stage_end, info, error as log_error

# ---------------------------------------------------------------------------
# Constants pulled from scoring_evaluator.py (kept in sync manually)
# ---------------------------------------------------------------------------
GLOBAL_BANNED_PHRASES = [
    "world-class", "top talent", "a-players", "rockstar", "ninja", "wizard",
    "skyrocket", "supercharge", "game-changer", "game-changing", "disruptor",
    "paradigm shift", "i hope this email finds you well", "hope this finds you well",
    "just wanted to reach out", "just following up", "circling back",
    "quick question", "quick chat", "synergize", "synergy", "leverage",
    "ecosystem", "don't miss out", "you'll regret", "per my last email",
    "per my last", "would love to", "excited to share", "years of experience",
    "cost arbitrage", "cost savings", "dramatically reduce", "cost reduction",
    "amazing opportunity", "as you may know", "best in class",
]

TRAINING_DATA_BUDGET_USD = 1.50  # Act III budget slice


# ---------------------------------------------------------------------------
# Hard-gate check (subset — deterministic gates only, no LLM)
# ---------------------------------------------------------------------------

def _passes_hard_gates(task: dict, output: str) -> tuple[bool, list[str]]:
    violations: list[str] = []
    out = output.lower()

    for phrase in GLOBAL_BANNED_PHRASES:
        if phrase in out:
            violations.append(f"global_banned_phrase: '{phrase}'")

    if re.search(r"\bbench\b(?!mark)", out):
        violations.append("external_bench_word")

    gt = task.get("ground_truth", {})
    for phrase in gt.get("banned_phrases", []):
        if phrase.lower() in out:
            violations.append(f"task_banned_phrase: '{phrase}'")

    brief = task.get("input_context", {}).get("prospect_brief", {})
    funding = brief.get("funding", {})
    stage_aliases = {
        "series_a": ["series a", "series-a"],
        "series_b": ["series b", "series-b"],
        "series_c": ["series c", "series-c"],
        "series_d": ["series d", "series-d"],
    }
    if isinstance(funding, dict) and funding:
        actual = funding.get("stage", "").lower()
        for stage, aliases in stage_aliases.items():
            if stage != actual:
                for alias in aliases:
                    if alias in out:
                        violations.append(f"funding_stage_mismatch: '{alias}' vs '{actual}'")

    bench = task.get("input_context", {}).get("bench_summary", {})
    for stack, info in bench.items():
        if not isinstance(info, dict) or "available_engineers" not in info:
            continue
        available = info["available_engineers"]
        if available == 0:
            patterns = [
                rf"\bhave {stack}\b", rf"{stack} engineer",
                rf"deploy.*{stack}", rf"{stack}.*available",
                rf"get.*{stack}.*started", rf"{stack}.*ready",
            ]
            for pat in patterns:
                if re.search(pat, out):
                    violations.append(f"bench_over_commitment: '{stack}' (available=0)")
                    break

    return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a B2B sales development representative for Tenacious, an engineering staffing firm.
Write outreach emails and replies following these rules exactly:

STYLE RULES (Tenacious Style Guide v2):
- Never use these banned words/phrases: {banned_list}
- Never use the word "bench" in prospect-facing messages (say "engineering team" or "available capacity")
- Use interrogative language when signal_confidence < 0.5
- Use assertive language only when signal_confidence >= 0.7
- Cold outreach must include a calendar link (gettenacious.com/cal)

GROUNDING RULES:
- Every factual claim must match the prospect brief exactly
- If signal_confidence is low or hiring_velocity is flat/insufficient, hedge claims with "may", "appears", "based on limited data"
- Never fabricate or upgrade a prospect's funding stage

BENCH HONESTY RULES:
- Never commit capacity for a stack listed with available_engineers=0
- If the needed stack has zero availability, explicitly disclaim: "We don't currently have [stack] engineers available"
- Do not use vague phrases like "several engineers" or "a few engineers"

Write ONLY the email body. No subject line. No meta-commentary."""


def _build_prompt(task: dict) -> list[dict]:
    ctx = task.get("input_context", {})
    brief = ctx.get("prospect_brief", {})
    bench = ctx.get("bench_summary", {})
    thread = ctx.get("prior_thread", [])
    category = task.get("metadata", {}).get("category", "")

    banned_list = ", ".join(f'"{p}"' for p in GLOBAL_BANNED_PHRASES[:10]) + ", and others"
    system = SYSTEM_PROMPT.format(banned_list=banned_list)

    # Summarise bench state — only include entries with the expected {available_engineers: N} shape
    bench_lines = []
    for stack, info in bench.items():
        if not isinstance(info, dict) or "available_engineers" not in info:
            continue
        bench_lines.append(f"  {stack}: {info['available_engineers']} available")
    bench_text = "\n".join(bench_lines) if bench_lines else "  (no bench data)"

    # Build signal description
    signal = brief.get("hiring_signal_brief", {})
    signal_parts = []
    if signal.get("open_roles") is not None:
        signal_parts.append(f"{signal['open_roles']} open roles")
    if signal.get("velocity_label"):
        signal_parts.append(f"velocity={signal['velocity_label']}")
    if signal.get("signal_confidence") is not None:
        signal_parts.append(f"confidence={signal['signal_confidence']:.2f}")
    if signal.get("ai_maturity_score") is not None:
        signal_parts.append(f"ai_maturity={signal['ai_maturity_score']}/3")
    signal_text = ", ".join(signal_parts) if signal_parts else "no signal data"

    funding = brief.get("funding", {})
    if isinstance(funding, dict) and funding:
        funding_text = (
            f"{funding.get('stage', 'unknown')} (${funding.get('amount_usd', 0):,}, "
            f"closed {funding.get('closed_at', 'unknown')})"
        )
    elif isinstance(funding, str) and funding:
        funding_text = funding
    else:
        funding_text = "no funding data"

    context_block = f"""Prospect: {brief.get('company_name', 'Unknown')} ({brief.get('domain', '')})
Employees: {brief.get('employee_count', 'unknown')}
Funding: {funding_text}
Signal: {signal_text}
Segment: {signal.get('segment', 'unknown')}

Available engineering capacity:
{bench_text}

Task category (what the failing output got wrong): {category}"""

    if thread and isinstance(thread, list):
        thread_text = "\n".join(
            f"{'Agent' if m.get('role') == 'agent' else 'Prospect'}: {m.get('content', '')}"
            for m in thread[-4:]
            if isinstance(m, dict)
        )
        user_content = (
            f"{context_block}\n\nPrior conversation:\n{thread_text}\n\n"
            "Write a compliant reply that addresses the prospect's message "
            "without violating any of the style, grounding, or bench honesty rules above."
        )
    elif thread and isinstance(thread, dict):
        # Synthesis tasks use keyed email dict — flatten to plain text
        thread_text = "\n".join(
            f"{k}: {v.get('body', v) if isinstance(v, dict) else v}"
            for k, v in list(thread.items())[-2:]
        )
        user_content = (
            f"{context_block}\n\nPrior conversation:\n{thread_text}\n\n"
            "Write a compliant reply that addresses the prospect's message "
            "without violating any of the style, grounding, or bench honesty rules above."
        )
    else:
        user_content = (
            f"{context_block}\n\n"
            "Write a compliant cold outreach email. "
            "Remember: include the calendar link if this is cold outreach, "
            "disclaim any zero-availability stacks, and hedge if signal confidence is below 0.5."
        )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# OpenRouter call
# ---------------------------------------------------------------------------

def _call_openrouter(messages: list[dict], model: str, api_key: str) -> tuple[str, int, int]:
    """Returns (content, tokens_in, tokens_out). Raises on error."""
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/10academy/sales-agent-evaluation-bench",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 400,
        },
        timeout=60,
    )
    res = response.json()
    if "error" in res:
        raise RuntimeError(f"OpenRouter error: {res['error']}")
    content = res["choices"][0]["message"]["content"].strip()
    usage = res.get("usage") or {}
    return content, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


# ---------------------------------------------------------------------------
# Contamination check against held-out (n-gram Jaccard)
# ---------------------------------------------------------------------------

def _ngrams(text: str, n: int = 8) -> set[str]:
    tokens = re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()
    return {" ".join(tokens[i: i + n]) for i in range(len(tokens) - n + 1)}


def _build_held_out_ngrams(n: int = 8) -> list[set[str]]:
    if not HELD_OUT_FILE.exists():
        return []
    ngram_sets = []
    for line in HELD_OUT_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        task = json.loads(line)
        text = task.get("candidate_output", "") + " " + json.dumps(
            task.get("input_context", {}).get("prospect_brief", {})
        )
        ngram_sets.append(_ngrams(text, n))
    return ngram_sets


def _chosen_contaminates_held_out(
    chosen: str, held_out_ngrams: list[set[str]], threshold: int = 3
) -> bool:
    chosen_ng = _ngrams(chosen)
    for ho_set in held_out_ngrams:
        overlap = len(chosen_ng & ho_set)
        if overlap >= threshold:
            return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(dry_run: bool = False, limit: int | None = None) -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and not dry_run:
        print("ERROR: OPENROUTER_API_KEY not set. Use --dry-run or set the env var.")
        sys.exit(1)

    router_cfg = json.loads(ROUTER_CONFIG.read_text())
    rewriter_model = router_cfg["families"]["openai"]["models"][0]
    rewriter_rates = router_cfg["families"]["openai"]["cost_per_1k_tokens"]

    tasks = [
        json.loads(line)
        for line in TRAIN_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if limit:
        tasks = tasks[:limit]

    OUTPUT_DIR.mkdir(exist_ok=True)
    held_out_ngrams = _build_held_out_ngrams()

    stage_start("training_data", f"Building {len(tasks)} preference pairs (model={rewriter_model})")
    info("training_data", f"Rewriter: {rewriter_model} | dry_run={dry_run} | tasks={len(tasks)}")

    pairs: list[dict] = []
    report_entries: list[dict] = []
    skipped = 0

    for i, task in enumerate(tasks):
        task_id = task.get("task_id", f"task_{i}")
        messages = _build_prompt(task)
        rejected_text = task.get("candidate_output", "")

        entry = {
            "task_id": task_id,
            "category": task.get("metadata", {}).get("category", ""),
            "source_mode": task.get("metadata", {}).get("source_mode", ""),
            "status": "pending",
            "retries": 0,
            "cost_usd": 0.0,
            "violations_on_rejected": [],
            "contaminated": False,
        }

        # Verify rejected output actually fails hard gates (sanity check)
        rejected_passes, rejected_violations = _passes_hard_gates(task, rejected_text)
        entry["violations_on_rejected"] = rejected_violations

        chosen_text = ""
        success = False

        if dry_run:
            # Stub output for testing without API calls
            chosen_text = (
                f"Hi — saw {task.get('input_context', {}).get('prospect_brief', {}).get('company_name', 'your company')} "
                f"is growing its engineering team. We have capacity across Python and data engineering "
                f"and can typically have engineers productive within two weeks. "
                f"Worth a conversation? gettenacious.com/cal"
            )
            success, _ = _passes_hard_gates(task, chosen_text)
            entry["status"] = "dry_run"
        else:
            for attempt in range(3):
                try:
                    chosen_text, tokens_in, tokens_out = _call_openrouter(
                        messages, rewriter_model, api_key
                    )
                    cost = (tokens_in / 1000 * rewriter_rates["input"]) + (
                        tokens_out / 1000 * rewriter_rates["output"]
                    )
                    entry["cost_usd"] += cost
                    log_cost(
                        "training_data",
                        f"chosen_rewrite:{task_id}",
                        rewriter_model,
                        tokens_in,
                        tokens_out,
                        cost,
                    )
                except BudgetExceededError as e:
                    print(f"\nBudget exceeded at task {task_id}: {e}")
                    entry["status"] = "budget_exceeded"
                    report_entries.append(entry)
                    _write_outputs(pairs, report_entries)
                    stage_end("training_data", len(pairs), f"Stopped early — budget exceeded")
                    return
                except Exception as e:
                    log_error("training_data", f"{task_id} attempt {attempt+1}: {e}")
                    time.sleep(2 ** attempt)
                    entry["retries"] += 1
                    continue

                gate_pass, gate_violations = _passes_hard_gates(task, chosen_text)
                if gate_pass:
                    success = True
                    break
                else:
                    entry["retries"] += 1
                    info(
                        "training_data",
                        f"{task_id} retry {attempt+1}: chosen failed gates {gate_violations[:2]}",
                    )

        if not success:
            entry["status"] = "skipped_chosen_failed_gates"
            skipped += 1
            report_entries.append(entry)
            continue

        # Contamination check: chosen output vs held-out
        if _chosen_contaminates_held_out(chosen_text, held_out_ngrams):
            entry["status"] = "skipped_contaminated"
            entry["contaminated"] = True
            skipped += 1
            report_entries.append(entry)
            info("training_data", f"{task_id} skipped — chosen contaminates held-out")
            continue

        # Build ORPO pair (TRL ORPOTrainer / CPOTrainer format)
        pair = {
            "prompt": messages,
            "chosen": [{"role": "assistant", "content": chosen_text}],
            "rejected": [{"role": "assistant", "content": rejected_text}],
            "metadata": {
                "task_id": task_id,
                "category": task.get("metadata", {}).get("category", ""),
                "source_mode": task.get("metadata", {}).get("source_mode", ""),
                "difficulty": task.get("metadata", {}).get("difficulty", ""),
                "rewriter_model": rewriter_model if not dry_run else "dry_run",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        pairs.append(pair)
        entry["status"] = "ok"
        report_entries.append(entry)

        if (i + 1) % 10 == 0:
            info(
                "training_data",
                f"Progress: {i+1}/{len(tasks)} tasks, {len(pairs)} pairs so far",
                {"pairs": len(pairs), "skipped": skipped},
            )

    _write_outputs(pairs, report_entries)

    total_cost = sum(e["cost_usd"] for e in report_entries)
    stage_end(
        "training_data",
        len(pairs),
        f"Done — {len(pairs)} pairs, {skipped} skipped, ${total_cost:.4f} spent",
    )
    print(f"\n{'='*60}")
    print(f"Pairs written : {len(pairs)}")
    print(f"Skipped       : {skipped}")
    print(f"Cost          : ${total_cost:.4f}")
    print(f"Output        : {PAIRS_FILE}")
    print(f"Report        : {REPORT_FILE}")
    _print_category_summary(pairs)


def _write_outputs(pairs: list[dict], report_entries: list[dict]) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(PAIRS_FILE, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    ok = sum(1 for e in report_entries if e["status"] == "ok")
    skipped = sum(1 for e in report_entries if e["status"] not in ("ok", "dry_run"))
    report = {
        "schema_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tasks": len(report_entries),
        "pairs_written": ok,
        "skipped": skipped,
        "total_cost_usd": round(sum(e["cost_usd"] for e in report_entries), 6),
        "rewriter_model": report_entries[0].get("rewriter_model", "") if report_entries else "",
        "contamination_threshold_ngrams": 3,
        "entries": report_entries,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def _print_category_summary(pairs: list[dict]) -> None:
    cats: dict[str, int] = {}
    for p in pairs:
        c = p.get("metadata", {}).get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1
    if cats:
        print("\nPairs by category:")
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"  {cat:<35} {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Path B ORPO preference pairs")
    parser.add_argument("--dry-run", action="store_true", help="Stub chosen outputs, no API calls")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N tasks")
    args = parser.parse_args()

    # Load .env if present
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    main(dry_run=args.dry_run, limit=args.limit)
