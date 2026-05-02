"""
pipeline_logger.py

Structured JSONL event logger for the build_dataset pipeline.
The Streamlit dashboard reads this file in near-real-time.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_FILE = Path(__file__).parent.parent / "pipeline_run.jsonl"

# Event types
STAGE_START = "stage_start"
STAGE_END = "stage_end"
TASK_BATCH = "task_batch"
COST_UPDATE = "cost_update"
ERROR = "error"
INFO = "info"


def _entry(event_type: str, stage: str, message: str, data: dict | None = None) -> dict:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "stage": stage,
        "msg": message,
        "data": data or {},
    }


def _write(entry: dict) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    # Also echo to stdout so the terminal shows progress
    ts = entry["ts"][11:19]
    print(f"  [{ts}] [{entry['stage']}] {entry['msg']}", flush=True)


def start_run(synth_enabled: bool) -> None:
    LOG_FILE.unlink(missing_ok=True)  # fresh log each run
    _write(_entry(STAGE_START, "pipeline", "Build started", {"synth": synth_enabled}))


def end_run(total: int, train: int, dev: int, held_out: int, budget: float) -> None:
    _write(_entry(
        STAGE_END, "pipeline", f"Build complete — {total} tasks",
        {"total": total, "train": train, "dev": dev, "held_out": held_out, "budget_usd": budget},
    ))


def stage_start(stage: str, msg: str = "") -> None:
    _write(_entry(STAGE_START, stage, msg or f"{stage} started"))


def stage_end(stage: str, count: int, msg: str = "") -> None:
    _write(_entry(STAGE_END, stage, msg or f"{stage} done — {count} tasks", {"count": count}))


def task_batch(stage: str, count: int, cumulative: int) -> None:
    _write(_entry(TASK_BATCH, stage, f"+{count} tasks (total so far: {cumulative})",
                  {"batch": count, "cumulative": cumulative}))


def cost_update(bucket: str, model: str, cost: float, running_total: float) -> None:
    _write(_entry(COST_UPDATE, bucket, f"${cost:.4f} ({model})",
                  {"cost": cost, "running_total": running_total, "model": model}))


def error(stage: str, msg: str) -> None:
    _write(_entry(ERROR, stage, f"ERROR: {msg}"))


def info(stage: str, msg: str, data: dict | None = None) -> None:
    _write(_entry(INFO, stage, msg, data))
