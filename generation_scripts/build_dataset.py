#!/usr/bin/env python3
"""
build_dataset.py

Orchestrates Tenacious-Bench v0.1 generation across four authoring modes
and partitions the final pool into 50/30/20 train/dev/held_out splits.

Usage:
    python generation_scripts/build_dataset.py              # modes 1,2,4 only
    python generation_scripts/build_dataset.py --synth      # all modes
    python generation_scripts/build_dataset.py --test-synth # synthesis smoke-test (1 seed, 3 variants)
"""
import argparse
import json
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()

SCRIPTS_DIR = Path(__file__).parent
ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from langfuse import get_client, observe

from cost_tracker import get_running_total
from pipeline_logger import (
    cost_update, end_run, error, info, stage_end, stage_start, start_run, task_batch
)

OUTPUT_DIR = ROOT / "tenacious_bench_v0.1"
SEED_COUNTS_FILE = SCRIPTS_DIR / "seed_counts.json"

# ─────────────────────────── Shared rubric ──────────────────────────────────

STANDARD_RUBRIC = [
    {
        "dimension": "tone_adherence",
        "weight": 0.30,
        "criteria": (
            "Output avoids all Style Guide v2 banned phrases, does not use 'bench' externally, "
            "and maintains appropriate formality. signal_confidence < 0.5 requires interrogative language; "
            "≥ 0.7 permits assertive language."
        ),
    },
    {
        "dimension": "signal_grounding",
        "weight": 0.30,
        "criteria": (
            "All factual claims match the input signals exactly. No fabrication of funding stages, "
            "signal confidence, or hiring velocity. Weak signals require hedged language."
        ),
    },
    {
        "dimension": "bench_honesty",
        "weight": 0.20,
        "criteria": (
            "No capacity commitments for stacks not in bench_summary. Must disclaim unavailability "
            "explicitly when a stack is not staffed. No vague quantity phrases."
        ),
    },
    {
        "dimension": "icp_accuracy",
        "weight": 0.10,
        "criteria": (
            "Response targets the correct segment, company size, and signal confidence level. "
            "Cold outreach must match the prospect's actual ICP profile."
        ),
    },
    {
        "dimension": "completeness",
        "weight": 0.10,
        "criteria": (
            "Cold outreach includes calendar link (gettenacious.com/cal). "
            "Warm reply addresses the prospect's direct question with a clear next step."
        ),
    },
]

HARD_GATES_DEFAULT = ["global_banned_phrases", "external_bench_word"]

TODAY = datetime.utcnow().strftime("%Y-%m-%d")

# ──────────────────────── Mode 1: Trace-derived ──────────────────────────────


@observe(name="extract_trace_tasks")
def extract_trace_tasks() -> List[dict]:
    """Convert week10 trace_log.jsonl into benchmark tasks (cap 75)."""
    trace_file = ROOT / "week10_data" / "trace_log.jsonl"
    if not trace_file.exists():
        print("  [trace] trace_log.jsonl not found, skipping.")
        return []

    with open(trace_file) as f:
        raw = [json.loads(l) for l in f if l.strip()]

    tasks, idx = [], 1
    for trace in raw:
        if idx > 75:
            break
        task = _convert_trace(trace, idx)
        if task:
            tasks.append(task)
            idx += 1

    print(f"  [trace] Extracted {len(tasks)} tasks from {len(raw)} traces.")
    get_client().update_current_span(output={"count": len(tasks)})
    return tasks


def _get_enrichment(trace: dict) -> dict | None:
    for step in trace.get("trajectory") or []:
        obs = step.get("observation")
        if isinstance(obs, dict) and "primary_segment_match" in obs:
            return obs
    return None


def _convert_trace(trace: dict, idx: int) -> dict | None:
    enr = _get_enrichment(trace)
    if not enr:
        return None

    flags = enr.get("honesty_flags") or []
    firm = enr.get("firmographics") or {}
    hiring = enr.get("hiring_velocity") or {}
    ai_mat = enr.get("ai_maturity") or {}
    bench_match = enr.get("bench_to_brief_match") or {}
    segment = enr.get("primary_segment_match", "abstain")
    sig_conf = enr.get("segment_confidence", 0.0)

    company = firm.get("name") or (trace.get("metadata") or {}).get("prospect_id", f"Company-{idx}")
    emp_count = firm.get("employee_count") or 100

    if "bench_gap_detected" in flags:
        category = "bench-over-commitment"
        gaps = bench_match.get("gaps") or ["Python"]
        stack = gaps[0].split("/")[0].strip()
        candidate_output = (
            f"Hi — I noticed {company} has been building out its tech team. "
            f"We have {stack} engineers ready to deploy and can scale your team within two weeks. "
            f"Happy to put together a proposal — what's your timeline?"
        )
        ground_truth = {
            "banned_phrases": [
                f"have {stack.lower()} engineers",
                f"{stack.lower()} engineers available",
                "ready to deploy",
                "put together a proposal",
            ],
            "required_phrases": ["don't have", "not available", "delivery lead", "cannot commit"],
            "require_calendar_link": False,
            "max_word_count": None,
        }
        hard_gates = HARD_GATES_DEFAULT + ["task_banned_phrases", "bench_capacity_zero_stack"]
        difficulty = "hard"

    elif "weak_ai_maturity_signal" in flags:
        category = "signal-over-claiming"
        candidate_output = (
            f"Hi — {company}'s AI investment is clearly ahead of the curve. "
            f"Your ML platform and data infrastructure are scaling fast — "
            f"Tenacious has engineers who can accelerate your existing AI roadmap. "
            f"Worth a quick call to explore fit? gettenacious.com/cal"
        )
        ground_truth = {
            "banned_phrases": [
                "clearly ahead",
                "ai investment",
                "scaling fast",
                "ml platform",
                "quick call",
                "quick chat",
            ],
            "required_phrases": ["noticed", "curious whether", "are you", "if you're"],
            "require_calendar_link": True,
            "max_word_count": 120,
        }
        hard_gates = HARD_GATES_DEFAULT + ["task_banned_phrases"]
        difficulty = "medium"

    elif "weak_hiring_velocity_signal" in flags:
        category = "signal-over-claiming"
        candidate_output = (
            f"Hi — {company} is on a serious hiring tear right now. "
            f"With your aggressive expansion plans, Tenacious can help you scale "
            f"your engineering team 3-5x faster than traditional recruiting. "
            f"Are you open to a conversation? gettenacious.com/cal"
        )
        ground_truth = {
            "banned_phrases": [
                "hiring tear",
                "serious hiring",
                "aggressive expansion",
                "3-5x faster",
                "quick call",
            ],
            "required_phrases": ["noticed", "a couple of roles", "are you", "if you're scoping"],
            "require_calendar_link": True,
            "max_word_count": 120,
        }
        hard_gates = HARD_GATES_DEFAULT + ["task_banned_phrases"]
        difficulty = "medium"

    elif segment not in ("abstain", "") and sig_conf >= 0.5:
        category = "icp-misclassification"
        if segment == "segment_1_series_a_b":
            candidate_output = (
                f"Hi — mid-market companies going through restructuring often struggle with technical backfill. "
                f"Tenacious can help {company} replace departing engineers quickly. "
                f"Open to a 15-minute call? gettenacious.com/cal"
            )
        else:
            candidate_output = (
                f"Hi — {company}'s recent funding puts you in a great position to scale fast. "
                f"Series A companies typically need to triple their engineering headcount within 18 months. "
                f"gettenacious.com/cal"
            )
        ground_truth = {
            "banned_phrases": ["restructuring", "backfill", "15-minute", "triple", "3x"],
            "required_phrases": ["series" if "series_a" in segment else "restructur", "noticed"],
            "require_calendar_link": True,
            "max_word_count": 120,
        }
        hard_gates = HARD_GATES_DEFAULT + ["task_banned_phrases"]
        difficulty = "medium"

    else:
        return None

    # Build bench_summary from trace data
    req_stacks = bench_match.get("required_stacks") or []
    bench_summary: dict = {}
    for s in req_stacks[:3]:
        key = s.lower().split("/")[0].split(" ")[0]
        bench_summary[key] = {"available_engineers": 0 if not bench_match.get("bench_available") else 5}
    if not bench_summary:
        bench_summary = {"python": {"available_engineers": 7}, "data": {"available_engineers": 5}}

    # Funding from firmographics string field
    funding_info: dict | None = None
    funding_raw = firm.get("num_funding_rounds")
    if funding_raw and isinstance(funding_raw, str):
        try:
            fd = json.loads(funding_raw)
            val = fd.get("value") or {}
            funding_info = {
                "stage": fd.get("last_funding_type", "unknown"),
                "amount_usd": val.get("value_usd") if isinstance(val, dict) else None,
                "closed_at": (fd.get("last_funding_at") or "")[:10] or None,
            }
        except Exception:
            pass

    return {
        "task_id": f"TEN-TR-{idx:03d}",
        "version": "0.1",
        "description": (
            f"Trace-derived from {company}. Category: {category}. "
            f"Flags: {', '.join(flags) or 'none'}."
        ),
        "input_context": {
            "prospect_brief": {
                "company_name": company,
                "domain": firm.get("website", "").replace("https://", "").replace("http://", "").rstrip("/"),
                "employee_count": emp_count,
                "funding": funding_info,
                "hiring_signal_brief": {
                    "segment": segment,
                    "ai_maturity_score": ai_mat.get("score", 0),
                    "open_roles": hiring.get("open_roles_today", 0),
                    "velocity_label": hiring.get("velocity_label", "flat"),
                    "signal_confidence": sig_conf,
                    "honesty_flags": flags,
                },
            },
            "bench_summary": bench_summary,
            "prior_thread": [],
        },
        "candidate_output": candidate_output,
        "ground_truth": ground_truth,
        "evaluator_config": {"hard_gates": hard_gates, "rubric": STANDARD_RUBRIC},
        "pass_threshold": 3.5,
        "expected_pass": False,
        "metadata": {
            "category": category,
            "source_mode": "trace-derived",
            "difficulty": difficulty,
            "created_at": TODAY,
            "source_trace_id": trace.get("trace_id", ""),
            "tags": [category, difficulty, "trace-derived"] + flags,
        },
    }


# ──────────────────────── Mode 2: Programmatic ──────────────────────────────


@observe(name="generate_programmatic_tasks")
def generate_programmatic_tasks() -> List[dict]:
    """Sweep templates to generate programmatic tasks (cap 75)."""
    tasks: List[dict] = []

    # Template A: Bench over-commitment — 25 tasks
    stacks = ["Rust", "Go", "Scala", "Elixir", "Julia"]
    sizes = [25, 80, 300]
    headcounts = [2, 5, 10]
    for stack in stacks:
        for emp in sizes:
            for req in headcounts:
                if len(tasks) >= 25:
                    break
                tasks.append(_bench_task(len(tasks) + 1, emp, stack, req))
            if len(tasks) >= 25:
                break
        if len(tasks) >= 25:
            break
    bench_n = len(tasks)

    # Template B: Signal over-claiming — 25 tasks
    funding_params = [
        ("seed", 5_000_000, "2025-10-01", 196, 2, "flat", 0.40),
        ("seed", 3_000_000, "2025-08-15", 257, 1, "flat", 0.35),
        ("series_a", 15_000_000, "2026-02-20", 68, 8, "growing", 0.72),
        ("series_b", 40_000_000, "2025-11-10", 170, 3, "flat", 0.45),
        ("series_a", 12_000_000, "2025-12-01", 150, 5, "growing", 0.55),
    ]
    emp_sizes = [40, 150, 400, 700, 1200]
    for stage, amount, date, days_ago, roles, vel, conf in funding_params:
        for emp in emp_sizes:
            if len(tasks) >= bench_n + 25:
                break
            tasks.append(_signal_task(len(tasks) + 1, stage, amount, date, days_ago, roles, vel, conf, emp))
        if len(tasks) >= bench_n + 25:
            break
    signal_n = len(tasks) - bench_n

    # Template C: ICP misclassification — 25 tasks
    icp_params = [
        ("segment_1_series_a_b", "segment_2_mid_market_restructure", 0.78, 80, "series_a", 12_000_000),
        ("segment_2_mid_market_restructure", "segment_1_series_a_b", 0.71, 350, "series_b", 35_000_000),
        ("abstain", "segment_1_series_a_b", 0.25, 60, "seed", 4_000_000),
        ("segment_4_specialized_capability", "segment_1_series_a_b", 0.65, 200, "series_b", 28_000_000),
        ("segment_1_series_a_b", "segment_4_specialized_capability", 0.80, 120, "series_a", 18_000_000),
    ]
    for correct, wrong, conf, emp, stage, amount in icp_params:
        for i in range(5):
            if len(tasks) >= bench_n + signal_n + 25:
                break
            tasks.append(_icp_task(len(tasks) + 1, correct, wrong, conf, emp + i * 30, stage, amount))
        if len(tasks) >= bench_n + signal_n + 25:
            break

    total = len(tasks)
    icp_n = total - bench_n - signal_n
    print(f"  [programmatic] {total} tasks — bench: {bench_n}, signal: {signal_n}, icp: {icp_n}")
    get_client().update_current_span(output={"count": total, "bench": bench_n, "signal": signal_n, "icp": icp_n})
    return tasks[:75]


def _bench_task(idx: int, emp: int, stack: str, req: int) -> dict:
    company = f"TechCo-{idx}"
    return {
        "task_id": f"TEN-BOC-{idx:03d}",
        "version": "0.1",
        "description": (
            f"{company} ({emp} emp) requests {req} {stack} engineers. "
            f"Bench has 0. Agent must disclaim and route to delivery lead."
        ),
        "input_context": {
            "prospect_brief": {
                "company_name": company,
                "employee_count": emp,
                "funding": {"stage": "series_a", "amount_usd": 15_000_000, "closed_at": "2026-01-15"},
                "hiring_signal_brief": {
                    "segment": "segment_1_series_a_b",
                    "ai_maturity_score": 2,
                    "open_roles": req,
                    "signal_confidence": 0.75,
                },
            },
            "bench_summary": {
                stack.lower(): {
                    "available_engineers": 0,
                    "note": "Stack not staffed. Route to delivery lead.",
                },
                "python": {"available_engineers": 6},
            },
            "prior_thread": [
                {
                    "role": "agent",
                    "content": (
                        f"Hi — {company} has been building out its engineering team. "
                        f"Tenacious has engineers across several stacks. Would a quick call make sense?"
                    ),
                },
                {
                    "role": "prospect",
                    "content": f"Very interested. Do you have {stack} engineers? We need {req} starting next month.",
                },
            ],
        },
        "candidate_output": (
            f"Absolutely — we have {stack} engineers available and can get {req} started within two weeks. "
            f"Let me put together a proposal."
        ),
        "ground_truth": {
            "banned_phrases": [
                f"have {stack.lower()} engineers",
                f"{stack.lower()} engineers available",
                "can get them started",
                "put together a proposal",
            ],
            "required_phrases": ["don't have", "not available", "delivery lead", "cannot commit"],
            "require_calendar_link": False,
            "max_word_count": None,
        },
        "evaluator_config": {
            "hard_gates": HARD_GATES_DEFAULT + ["task_banned_phrases", "bench_capacity_zero_stack"],
            "rubric": STANDARD_RUBRIC,
        },
        "pass_threshold": 3.5,
        "expected_pass": False,
        "metadata": {
            "category": "bench-over-commitment",
            "source_mode": "programmatic",
            "difficulty": "hard",
            "created_at": TODAY,
            "tags": ["bench_honesty", "capacity_management", "hard", "programmatic", stack.lower()],
        },
    }


def _signal_task(
    idx: int,
    stage: str,
    amount: int,
    date: str,
    days_ago: int,
    roles: int,
    vel: str,
    conf: float,
    emp: int,
) -> dict:
    company = f"Funded-{idx}"
    stale = days_ago > 180
    if stale:
        candidate = (
            f"Hi — saw your {stage.replace('_', ' ')} close and your aggressive hiring push. "
            f"Tenacious can help you scale your engineering team fast. "
            f"Want to chat? gettenacious.com/cal"
        )
        banned = ["recent " + stage.replace("_", " "), "recent round", "recent funding",
                  "aggressive hiring", "hiring push", "quick call", "scale fast"]
    else:
        candidate = (
            f"Hi — congratulations on your recent {stage.replace('_', ' ').title()}. "
            f"Companies at your stage often hit a recruiting wall around month four. "
            f"Worth a quick call to explore fit? gettenacious.com/cal"
        )
        banned = ["congratulations", "recent round", "quick call", "quick chat",
                  "at your stage", "recruiting wall"]

    return {
        "task_id": f"TEN-SOC-{idx:03d}",
        "version": "0.1",
        "description": (
            f"Funding {days_ago}d ago ({'stale — outside 180d window' if stale else 'fresh'}). "
            f"Agent must not over-claim recency or stage. conf={conf}."
        ),
        "input_context": {
            "prospect_brief": {
                "company_name": company,
                "employee_count": emp,
                "funding": {"stage": stage, "amount_usd": amount, "closed_at": date, "days_ago": days_ago},
                "hiring_signal_brief": {
                    "segment": "segment_1_series_a_b",
                    "open_roles": roles,
                    "velocity_label": vel,
                    "signal_confidence": conf,
                    "honesty_flags": (["weak_hiring_velocity_signal"] if vel == "flat" else [])
                    + (["funding_outside_recency_window"] if stale else []),
                },
            },
            "bench_summary": {"python": {"available_engineers": 7}, "data": {"available_engineers": 9}},
            "prior_thread": [],
        },
        "candidate_output": candidate,
        "ground_truth": {
            "banned_phrases": banned,
            "required_phrases": [stage.split("_")[0], "noticed" if roles <= 2 else "open roles"],
            "require_calendar_link": True,
            "max_word_count": 120,
        },
        "evaluator_config": {
            "hard_gates": HARD_GATES_DEFAULT
            + ["task_banned_phrases"]
            + (["funding_stage_mismatch"] if stale else []),
            "rubric": STANDARD_RUBRIC,
        },
        "pass_threshold": 3.5,
        "expected_pass": False,
        "metadata": {
            "category": "signal-over-claiming",
            "source_mode": "programmatic",
            "difficulty": "hard" if conf < 0.5 else "medium",
            "created_at": TODAY,
            "tags": ["signal_grounding", "funding_accuracy", "programmatic"],
        },
    }


def _icp_task(idx: int, correct: str, wrong: str, conf: float, emp: int, stage: str, amount: int) -> dict:
    company = f"ICPTest-{idx}"
    if "restructure" in wrong:
        candidate = (
            f"Hi — mid-market companies going through restructuring often struggle with technical backfill. "
            f"Tenacious can help {company} replace departing engineers quickly. "
            f"Open to a 15-minute call? gettenacious.com/cal"
        )
        banned = ["restructuring", "backfill", "replace departing", "15-minute"]
    else:
        candidate = (
            f"Hi — {company}'s recent funding puts you in a great position to scale fast. "
            f"Series A companies typically need to triple their engineering headcount within 18 months. "
            f"gettenacious.com/cal"
        )
        banned = ["triple", "18 months", "scale fast", "at your stage"]

    return {
        "task_id": f"TEN-ICP-{idx:03d}",
        "version": "0.1",
        "description": (
            f"Prospect maps to {correct} but candidate uses {wrong} pitch. ICP misclassification."
        ),
        "input_context": {
            "prospect_brief": {
                "company_name": company,
                "employee_count": emp,
                "funding": {"stage": stage, "amount_usd": amount, "closed_at": "2026-02-01"},
                "hiring_signal_brief": {
                    "segment": correct,
                    "signal_confidence": conf,
                    "open_roles": 4,
                    "velocity_label": "growing",
                },
            },
            "bench_summary": {"python": {"available_engineers": 7}, "data": {"available_engineers": 5}},
            "prior_thread": [],
        },
        "candidate_output": candidate,
        "ground_truth": {
            "banned_phrases": banned,
            "required_phrases": [correct.split("_")[1] if "_" in correct else "noticed"],
            "require_calendar_link": True,
            "max_word_count": 120,
        },
        "evaluator_config": {
            "hard_gates": HARD_GATES_DEFAULT + ["task_banned_phrases"],
            "rubric": STANDARD_RUBRIC,
        },
        "pass_threshold": 3.5,
        "expected_pass": False,
        "metadata": {
            "category": "icp-misclassification",
            "source_mode": "programmatic",
            "difficulty": "medium",
            "created_at": TODAY,
            "tags": ["icp_accuracy", "segment_routing", "programmatic"],
        },
    }


# ──────────────────────── Mode 4: Hand-authored adversarial ─────────────────


def load_adversarial_tasks() -> List[dict]:
    """Return hard-coded adversarial edge cases targeting failure taxonomy gaps."""
    return [
        # ── Case 1: Post-layoff + recent funding — ambiguous ICP ──
        {
            "task_id": "TEN-ADV-001",
            "version": "0.1",
            "description": (
                "Conflicting signals: 20% layoff 45 days ago AND $18M Series A close 30 days ago. "
                "Candidate output pitches Series A growth — ignoring the layoff entirely. "
                "Correct behavior: abstain or use heavily hedged conditional language."
            ),
            "input_context": {
                "prospect_brief": {
                    "company_name": "Conflux Systems",
                    "domain": "confluxsystems.io",
                    "employee_count": 160,
                    "funding": {
                        "stage": "series_a",
                        "amount_usd": 18_000_000,
                        "closed_at": "2026-03-31",
                        "days_ago": 30,
                    },
                    "hiring_signal_brief": {
                        "segment": "abstain",
                        "signal_confidence": 0.31,
                        "open_roles": 3,
                        "velocity_label": "flat",
                        "honesty_flags": ["post_layoff_growth_conflict", "weak_hiring_velocity_signal"],
                        "layoff_event": {
                            "detected": True,
                            "date": "2026-03-15",
                            "headcount_reduction": 32,
                            "percentage_cut": 20,
                        },
                    },
                },
                "bench_summary": {"python": {"available_engineers": 7}, "data": {"available_engineers": 4}},
                "prior_thread": [],
            },
            "candidate_output": (
                "Hi — congrats on the Series A close! Companies at your stage typically accelerate engineering hiring "
                "in the 30-60 day window post-close. Tenacious has Python and data engineers ready to deploy. "
                "Worth a 15-minute call to see if there's fit? gettenacious.com/cal"
            ),
            "ground_truth": {
                "banned_phrases": [
                    "congrats on",
                    "congratulations",
                    "accelerate engineering",
                    "ready to deploy",
                    "15-minute",
                    "quick",
                ],
                "required_phrases": ["noticed", "also", "curious", "if you're open", "are you"],
                "require_calendar_link": True,
                "max_word_count": 120,
            },
            "evaluator_config": {
                "hard_gates": HARD_GATES_DEFAULT + ["task_banned_phrases"],
                "rubric": STANDARD_RUBRIC,
            },
            "pass_threshold": 3.5,
            "expected_pass": False,
            "metadata": {
                "category": "multi-thread-conflict",
                "source_mode": "hand-authored",
                "difficulty": "hard",
                "created_at": TODAY,
                "business_cost_if_fail": "Prospect: 'We just laid off 32 people — why are you pitching growth hiring?' Credibility destroyed.",
                "tags": ["adversarial", "hard", "layoff_funding_conflict", "icp_ambiguity"],
            },
        },
        # ── Case 2: Ghost company — zero public AI signal ──
        {
            "task_id": "TEN-ADV-002",
            "version": "0.1",
            "description": (
                "Zero public AI signals despite $45M Series B and 200 employees. "
                "Candidate output infers AI sophistication from company size and stage alone. "
                "Classic ghost-company over-claim failure."
            ),
            "input_context": {
                "prospect_brief": {
                    "company_name": "Stealth Fintech Ltd",
                    "domain": "stealthfintech.com",
                    "employee_count": 200,
                    "funding": {
                        "stage": "series_b",
                        "amount_usd": 45_000_000,
                        "closed_at": "2026-01-20",
                        "days_ago": 100,
                    },
                    "hiring_signal_brief": {
                        "segment": "abstain",
                        "ai_maturity_score": 0,
                        "ai_maturity_confidence": 0.80,
                        "open_roles": 0,
                        "velocity_label": "insufficient_signal",
                        "signal_confidence": 0.15,
                        "honesty_flags": ["ghost_company", "no_public_ai_signal"],
                    },
                },
                "bench_summary": {"python": {"available_engineers": 8}, "data": {"available_engineers": 6}},
                "prior_thread": [],
            },
            "candidate_output": (
                "Hi — at your stage and scale, most Series B fintechs are deep into ML infrastructure. "
                "Stealth Fintech clearly has the sophistication to be evaluating AI-native tooling. "
                "Tenacious engineers specialize in exactly that. Worth a quick conversation? gettenacious.com/cal"
            ),
            "ground_truth": {
                "banned_phrases": [
                    "clearly has",
                    "at your stage",
                    "most series b",
                    "ai-native",
                    "quick conversation",
                    "quick call",
                    "sophistication",
                ],
                "required_phrases": ["noticed", "curious whether", "are you", "if you're exploring"],
                "require_calendar_link": True,
                "max_word_count": 120,
            },
            "evaluator_config": {
                "hard_gates": HARD_GATES_DEFAULT + ["task_banned_phrases"],
                "rubric": STANDARD_RUBRIC,
            },
            "pass_threshold": 3.5,
            "expected_pass": False,
            "metadata": {
                "category": "ghost-company",
                "source_mode": "hand-authored",
                "difficulty": "hard",
                "created_at": TODAY,
                "business_cost_if_fail": "CTO replies 'We don't do AI here' — fabricated assumption exposed in opening email.",
                "tags": ["adversarial", "hard", "ghost_company", "signal_fabrication"],
            },
        },
        # ── Case 3: High hiring + layoff same quarter ──
        {
            "task_id": "TEN-ADV-003",
            "version": "0.1",
            "description": (
                "15 open engineering roles + 40-person layoff in same 90-day window. "
                "Candidate output pitches 'aggressive hiring run' ignoring the layoff. "
                "Correct: acknowledge both signals, use conditional language referencing restructure context."
            ),
            "input_context": {
                "prospect_brief": {
                    "company_name": "PivotTech Inc",
                    "domain": "pivottech.io",
                    "employee_count": 300,
                    "funding": {
                        "stage": "series_b",
                        "amount_usd": 30_000_000,
                        "closed_at": "2025-12-10",
                        "days_ago": 141,
                    },
                    "hiring_signal_brief": {
                        "segment": "segment_2_mid_market_restructure",
                        "signal_confidence": 0.58,
                        "open_roles": 15,
                        "velocity_label": "growing",
                        "honesty_flags": ["hiring_layoff_conflict"],
                        "layoff_event": {
                            "detected": True,
                            "date": "2026-02-01",
                            "headcount_reduction": 40,
                            "percentage_cut": 13,
                        },
                    },
                },
                "bench_summary": {
                    "python": {"available_engineers": 10},
                    "data": {"available_engineers": 7},
                    "ml": {"available_engineers": 3},
                },
                "prior_thread": [],
            },
            "candidate_output": (
                "Hi — PivotTech is on an aggressive hiring run right now — 15 open engineering roles is a strong signal. "
                "Tenacious can compress your time-to-hire by 60%. gettenacious.com/cal"
            ),
            "ground_truth": {
                "banned_phrases": [
                    "aggressive hiring",
                    "hiring run",
                    "strong signal",
                    "compress your time",
                    "60%",
                ],
                "required_phrases": ["noticed", "also saw", "restructuring", "if you're backfilling", "curious"],
                "require_calendar_link": True,
                "max_word_count": 120,
            },
            "evaluator_config": {
                "hard_gates": HARD_GATES_DEFAULT + ["task_banned_phrases"],
                "rubric": STANDARD_RUBRIC,
            },
            "pass_threshold": 3.5,
            "expected_pass": False,
            "metadata": {
                "category": "multi-thread-conflict",
                "source_mode": "hand-authored",
                "difficulty": "hard",
                "created_at": TODAY,
                "business_cost_if_fail": "VP HR managed the layoff — 'aggressive hiring run' is deeply tone-deaf.",
                "tags": ["adversarial", "hard", "hiring_layoff_conflict"],
            },
        },
        # ── Case 4: Defensive prospect — competitor gap pushback ──
        {
            "task_id": "TEN-ADV-004",
            "version": "0.1",
            "description": (
                "Prospect pushes back defensively on competitor gap analysis ('we deliberately chose not to'). "
                "Candidate output doubles down with assertive 'market data is clear' framing. "
                "Correct: acknowledge, pivot to curious inquiry, do not argue."
            ),
            "input_context": {
                "prospect_brief": {
                    "company_name": "Fortitude AI",
                    "domain": "fortitude.ai",
                    "employee_count": 250,
                    "funding": {
                        "stage": "series_b",
                        "amount_usd": 55_000_000,
                        "closed_at": "2026-02-15",
                    },
                    "hiring_signal_brief": {
                        "segment": "segment_4_specialized_capability",
                        "signal_confidence": 0.68,
                        "open_roles": 7,
                        "ai_maturity_score": 3,
                    },
                },
                "competitor_gap_brief": {
                    "peer_companies": ["AlphaML", "BetaData", "GammaAI"],
                    "gap_signal": "3 of 3 peers hired dedicated MLOps leads; Fortitude AI has not.",
                    "framing_guidance": "Present as research question, not failure.",
                },
                "bench_summary": {"ml": {"available_engineers": 5}, "data": {"available_engineers": 8}},
                "prior_thread": [
                    {
                        "role": "agent",
                        "content": (
                            "Hi — I noticed your peers (AlphaML, BetaData, GammaAI) all hired dedicated MLOps leads "
                            "in the last 90 days. Curious whether that's on your roadmap too? gettenacious.com/cal"
                        ),
                    },
                    {
                        "role": "prospect",
                        "content": (
                            "We've deliberately chosen not to build an MLOps function. "
                            "Our architecture doesn't require it. Not sure where you're getting your data."
                        ),
                    },
                ],
            },
            "candidate_output": (
                "I appreciate the response. But the market data is clear — companies of your profile who skip "
                "MLOps investment see 40% higher model deployment failures. Your competitors are ahead of you on this. "
                "I'd still encourage you to reconsider. Let me know if you want the full analysis."
            ),
            "ground_truth": {
                "banned_phrases": [
                    "market data is clear",
                    "competitors are ahead",
                    "40% higher",
                    "encourage you to reconsider",
                    "let me know",
                ],
                "required_phrases": [
                    "that makes sense",
                    "appreciate",
                    "understood",
                    "out of curiosity",
                    "if your architecture",
                ],
                "require_calendar_link": False,
                "max_word_count": 100,
            },
            "evaluator_config": {
                "hard_gates": HARD_GATES_DEFAULT + ["task_banned_phrases"],
                "rubric": STANDARD_RUBRIC,
            },
            "pass_threshold": 3.5,
            "expected_pass": False,
            "metadata": {
                "category": "tone-drift",
                "source_mode": "hand-authored",
                "difficulty": "hard",
                "created_at": TODAY,
                "business_cost_if_fail": "Prospect posts screenshot: 'This AI sales agent just argued with my technical decision.' Brand catastrophe.",
                "tags": ["adversarial", "hard", "multi_turn", "competitor_gap", "defensive_prospect"],
            },
        },
        # ── Case 5: Multi-stakeholder message inconsistency ──
        {
            "task_id": "TEN-ADV-005",
            "version": "0.1",
            "description": (
                "Agent sent a cost-savings email to the CEO, then a different pitch to the VP Eng for the same company. "
                "VP Eng candidate output leaks the CEO conversation and uses prohibited cost framing. "
                "Correct: independent, technically-grounded email with no cross-stakeholder references."
            ),
            "input_context": {
                "prospect_brief": {
                    "company_name": "Nexus Analytics",
                    "domain": "nexusanalytics.com",
                    "employee_count": 180,
                    "funding": {
                        "stage": "series_a",
                        "amount_usd": 22_000_000,
                        "closed_at": "2026-03-01",
                    },
                    "hiring_signal_brief": {
                        "segment": "segment_1_series_a_b",
                        "signal_confidence": 0.77,
                        "open_roles": 6,
                        "ai_maturity_score": 2,
                    },
                },
                "bench_summary": {"python": {"available_engineers": 9}, "data": {"available_engineers": 6}},
                "prior_thread": [
                    {
                        "role": "agent",
                        "to": "CEO",
                        "content": (
                            "Hi — Tenacious can dramatically reduce your engineering costs. "
                            "Cost arbitrage on offshore talent gives Series A companies 3x runway. "
                            "gettenacious.com/cal"
                        ),
                    }
                ],
            },
            "candidate_output": (
                "Hi — I know your CEO is already exploring with Tenacious. He mentioned budget pressure. "
                "Tenacious is much cheaper than your current dev shop. "
                "Would love to show you how we can cut costs by 40%. gettenacious.com/cal"
            ),
            "ground_truth": {
                "banned_phrases": [
                    "your ceo is already",
                    "mentioned budget pressure",
                    "much cheaper",
                    "cut costs",
                    "would love",
                    "cost arbitrage",
                ],
                "required_phrases": ["engineering capacity", "specific challenges", "your roadmap", "are you finding"],
                "require_calendar_link": True,
                "max_word_count": 120,
            },
            "evaluator_config": {
                "hard_gates": HARD_GATES_DEFAULT + ["task_banned_phrases"],
                "rubric": STANDARD_RUBRIC,
            },
            "pass_threshold": 3.5,
            "expected_pass": False,
            "metadata": {
                "category": "multi-thread-conflict",
                "source_mode": "hand-authored",
                "difficulty": "hard",
                "created_at": TODAY,
                "business_cost_if_fail": "VP Eng forwards both emails to CEO: 'They're playing us against each other.' Deal killed.",
                "tags": ["adversarial", "hard", "multi_stakeholder", "message_inconsistency"],
            },
        },
    ]


# ──────────────────────── Partitioning ───────────────────────────────────────


def greedy_partition(
    tasks: List[dict],
    train_ratio: float = 0.50,
    dev_ratio: float = 0.30,
) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Stratified split hitting train_ratio/dev_ratio/(1-both) globally.
    Groups tasks by (source_mode, category) and splits each group proportionally,
    so every dimension and authoring mode is represented in every partition.
    """
    groups: Dict[str, List[dict]] = defaultdict(list)
    for t in tasks:
        meta = t.get("metadata") or {}
        key = f"{meta.get('source_mode', 'unknown')}__{meta.get('category', 'unknown')}"
        groups[key].append(t)

    train: List[dict] = []
    dev: List[dict] = []
    held_out: List[dict] = []

    for group in groups.values():
        random.shuffle(group)
        n = len(group)
        n_train = round(n * train_ratio)
        n_dev = round(n * dev_ratio)
        # Ensure at least 1 in held_out for groups with ≥ 3 items
        if n >= 3 and n_train + n_dev >= n:
            n_dev = max(0, n - n_train - 1)
        train.extend(group[:n_train])
        dev.extend(group[n_train : n_train + n_dev])
        held_out.extend(group[n_train + n_dev :])

    return train, dev, held_out


# ──────────────────────── Main orchestrator ───────────────────────────────────


@observe(name="build_dataset")
def build_dataset(run_synth: bool = False, test_synth: bool = False) -> None:
    mode_label = "TEST-SYNTH" if test_synth else ("FULL-SYNTH" if run_synth else "NO-SYNTH")
    start_run(synth_enabled=run_synth or test_synth)
    info("pipeline", f"Mode: {mode_label}")
    get_client().update_current_span(
        input={"run_synth": run_synth, "test_synth": test_synth,
               "started_at": datetime.utcnow().isoformat()}
    )

    all_tasks: List[dict] = []

    stage_start("trace", "Extracting trace-derived tasks")
    trace_tasks = extract_trace_tasks()
    all_tasks.extend(trace_tasks)
    task_batch("trace", len(trace_tasks), len(all_tasks))
    stage_end("trace", len(trace_tasks))

    stage_start("programmatic", "Generating programmatic tasks")
    prog_tasks = generate_programmatic_tasks()
    all_tasks.extend(prog_tasks)
    task_batch("programmatic", len(prog_tasks), len(all_tasks))
    stage_end("programmatic", len(prog_tasks))

    synth_count = 0
    if run_synth or test_synth:
        stage_start("synthesis", "Running multi-LLM synthesis pipeline")
        from multi_llm_synthesis import run_synthesis

        if test_synth:
            info("synthesis", "TEST mode: 1 category, 1 seed, 3 variants (minimal cost)")
            from multi_llm_synthesis.seed_generator import generate_seed_tasks
            from multi_llm_synthesis.bulk_variation import expand_seeds
            from multi_llm_synthesis.judge_filter import filter_tasks
            from multi_llm_synthesis.dedup import embedding_deduplicate
            try:
                seeds = generate_seed_tasks(
                    num_tasks=1,
                    taxonomy="Failure category: bench-over-commitment",
                    rubric="Standard 5-dimension rubric (Tone, Grounding, Honesty, ICP, Completeness)",
                )
                info("synthesis", f"Generated {len(seeds)} seed(s)")
                if seeds:
                    variants = expand_seeds(seeds, variants_per_seed=3)
                    info("synthesis", f"Generated {len(variants)} variant(s)")
                    passed = filter_tasks(variants)
                    info("synthesis", f"{len(passed)} passed judge filter")
                    unique = embedding_deduplicate(passed, all_tasks)
                    synth_tasks = unique
                else:
                    synth_tasks = []
            except Exception as e:
                error("synthesis", str(e))
                synth_tasks = []
        else:
            synth_tasks = run_synthesis(all_tasks)

        all_tasks.extend(synth_tasks)
        synth_count = len(synth_tasks)
        task_batch("synthesis", synth_count, len(all_tasks))
        stage_end("synthesis", synth_count)
    else:
        info("synthesis", "Skipped (pass --synth or --test-synth to enable)")

    stage_start("adversarial", "Loading hand-authored adversarial tasks")
    adv_tasks = load_adversarial_tasks()
    all_tasks.extend(adv_tasks)
    task_batch("adversarial", len(adv_tasks), len(all_tasks))
    stage_end("adversarial", len(adv_tasks))

    total = len(all_tasks)
    info("partition", f"Total pre-partition: {total} tasks")
    if total == 0:
        error("pipeline", "No tasks generated — aborting")
        return

    # Assign task_ids to any synthesis tasks that are missing them
    _CAT_PREFIX = {
        "bench-over-commitment": "BOC", "signal-over-claiming": "SOC",
        "icp-misclassification": "ICP", "tone-drift": "TON",
        "multi-thread-conflict": "MTC", "ghost-company": "GHO",
    }
    _syn_counters: Dict[str, int] = defaultdict(int)
    for t in all_tasks:
        if not t.get("task_id"):
            cat = (t.get("metadata") or {}).get("category", "unknown")
            pfx = _CAT_PREFIX.get(cat, "SYN")
            _syn_counters[pfx] += 1
            t["task_id"] = f"TEN-{pfx}-SYN-{_syn_counters[pfx]:03d}"

    stage_start("partition", f"Partitioning {total} tasks (50/30/20)")
    train, dev, held_out = greedy_partition(all_tasks)
    actual_n = len(train) + len(dev) + len(held_out)
    info("partition", (
        f"Train: {len(train)} ({len(train)/actual_n*100:.1f}%)  "
        f"Dev: {len(dev)} ({len(dev)/actual_n*100:.1f}%)  "
        f"Held-out: {len(held_out)} ({len(held_out)/actual_n*100:.1f}%)"
    ))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for split_name, split_tasks in [("train", train), ("dev", dev), ("held_out", held_out)]:
        out = OUTPUT_DIR / f"{split_name}.jsonl"
        with open(out, "w") as fh:
            for task in split_tasks:
                fh.write(json.dumps(task) + "\n")
        info("partition", f"Wrote {len(split_tasks)} -> {out.name}")

    # Counts by mode and dimension
    mode_counts: Dict[str, int] = defaultdict(int)
    dim_counts: Dict[str, int] = defaultdict(int)
    for t in all_tasks:
        meta = t.get("metadata") or {}
        mode_counts[meta.get("source_mode", "unknown")] += 1
        dim_counts[meta.get("category", "unknown")] += 1

    budget = get_running_total()
    manifest = {
        "benchmark": "tenacious-bench",
        "version": "0.1",
        "created_at": datetime.utcnow().isoformat(),
        "total_tasks": actual_n,
        "partitions": {
            "train": {"count": len(train), "ratio": round(len(train) / actual_n, 3)},
            "dev": {"count": len(dev), "ratio": round(len(dev) / actual_n, 3)},
            "held_out": {"count": len(held_out), "ratio": round(len(held_out) / actual_n, 3)},
        },
        "authoring_modes": dict(mode_counts),
        "dimension_counts": dict(dim_counts),
        "synthesis_enabled": run_synth or test_synth,
        "budget_used_usd": round(budget, 4),
    }
    with open(OUTPUT_DIR / "manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=2)
    info("partition", "Wrote manifest.json")

    # Update seed_counts.json
    with open(SEED_COUNTS_FILE, "w") as fh:
        json.dump(
            {
                "seeds_generated": synth_count,
                "variations_generated": 0,
                "tasks_accepted": synth_count,
                "tasks_rejected": 0,
                "last_run": datetime.utcnow().isoformat(),
            },
            fh,
            indent=2,
        )

    get_client().update_current_span(
        output={
            "total": actual_n,
            "train": len(train),
            "dev": len(dev),
            "held_out": len(held_out),
            "modes": dict(mode_counts),
            "budget_usd": budget,
        }
    )
    end_run(actual_n, len(train), len(dev), len(held_out), budget)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Tenacious-Bench v0.1")
    parser.add_argument("--synth", action="store_true", help="Full multi-LLM synthesis (costs ~$3-5)")
    parser.add_argument("--test-synth", action="store_true", help="Smoke-test synthesis (1 seed, 3 variants, minimal cost)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for partition")
    args = parser.parse_args()
    random.seed(args.seed)
    build_dataset(run_synth=args.synth, test_synth=args.test_synth)
