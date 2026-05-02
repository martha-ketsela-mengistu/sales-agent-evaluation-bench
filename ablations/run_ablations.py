"""
ablations/run_ablations.py

Ablation runner for Tenacious-Bench v0.1 Path B ORPO judge.

Methods compared
----------------
deterministic   Hard-gate + heuristic rubric; no LLM. Always runs.
claude          Pipeline A LLM judge (claude-sonnet-4-6). Week 10 baseline for Delta A.
                Requires ANTHROPIC_API_KEY.
orpo            ORPO LoRA-tuned Qwen judge. Requires CUDA + adapter on HuggingFace.
untrained_qwen  Same Qwen backbone, no LoRA. Prompt-engineered baseline for Delta B.

Metrics
-------
detection_rate  Fraction of expected_pass=False tasks correctly scored FAIL (TNR).
                All 59 held_out tasks have expected_pass=False, so this is the
                primary metric — higher = better judge.
delta_a         orpo.detection_rate − claude.detection_rate
delta_b         orpo.detection_rate − untrained_qwen.detection_rate
bootstrap_ci_95 95% CI on each delta via 2 000-resample paired bootstrap.
                p<0.05 (one-sided) when CI lower bound > 0.

Target: Delta A ≥ +0.03 (3 pp) per methodology_rationale.md.

Usage
-----
  python ablations/run_ablations.py                         # det + claude baselines
  python ablations/run_ablations.py --no-llm                # deterministic only
  python ablations/run_ablations.py --hf-repo marthaket/tenacious-judge-orpo-qwen
  python ablations/run_ablations.py --output ablation_results.json
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scoring_evaluator import score_task, load_tasks  # noqa: E402

JUDGE_SYSTEM_PROMPT = (
    "You are a Tenacious sales evaluation judge. "
    "Read the prospect context and email draft, then output exactly one word: PASS or FAIL.\n\n"
    "Output FAIL if ANY of the following are true:\n"
    "  - The word 'bench' appears (not as part of 'benchmark')\n"
    "  - A global banned phrase appears (world-class, rockstar, synergy, leverage, "
    "skyrocket, game-changer, would love to, excited to share, etc.)\n"
    "  - A task-specific banned phrase listed in the context appears\n"
    "  - A grounding claim is made without support from the prospect data\n"
    "  - A capacity commitment is made for a stack with 0 available engineers\n"
    "  - The word count exceeds the allowed limit\n\n"
    "Otherwise output PASS.\n"
    "Output ONLY the single word."
)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def detection_rate(results: list[dict]) -> float:
    """TNR: fraction of expected_pass=False tasks correctly scored FAIL."""
    labelled = [r for r in results if r.get("expected_pass") is False]
    if not labelled:
        return 0.0
    return sum(1 for r in labelled if not r["passed"]) / len(labelled)


def paired_bootstrap(
    base: list[dict],
    target: list[dict],
    n_resamples: int = 2000,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Returns (delta, ci_lo_95, ci_hi_95) for target − base detection_rate."""
    assert len(base) == len(target), "result lists must align task-for-task"
    n = len(base)
    rng = random.Random(seed)
    pairs = list(zip(base, target))
    deltas = []
    for _ in range(n_resamples):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        b = [p[0] for p in sample]
        t = [p[1] for p in sample]
        deltas.append(detection_rate(t) - detection_rate(b))
    deltas.sort()
    observed = detection_rate(target) - detection_rate(base)
    return observed, deltas[int(0.025 * n_resamples)], deltas[int(0.975 * n_resamples)]


# ---------------------------------------------------------------------------
# Pipeline A runners (deterministic + Claude)
# ---------------------------------------------------------------------------

def run_pipeline_a(tasks: list[dict], use_llm: bool) -> list[dict]:
    label = "claude" if use_llm else "deterministic"
    print(f"  [{label}] scoring {len(tasks)} tasks...", flush=True)
    results = []
    for i, t in enumerate(tasks):
        if (i + 1) % 10 == 0:
            print(f"    {i + 1}/{len(tasks)}", flush=True)
        results.append(score_task(t, use_llm=use_llm))
    return results


# ---------------------------------------------------------------------------
# Qwen judge runner (ORPO adapter or untrained baseline)
# ---------------------------------------------------------------------------

def _format_judge_input(task: dict) -> str:
    ctx = task.get("input_context", {})
    brief = ctx.get("prospect_brief", {})
    bench = ctx.get("bench_summary", {})
    gt = task.get("ground_truth", {})

    lines = [
        f"Company: {brief.get('company_name', 'Unknown')}",
        f"Employees: {brief.get('employee_count', '?')}",
        f"Funding: {brief.get('funding') or 'unknown'}",
    ]
    sig = brief.get("hiring_signal_brief", {})
    if sig:
        lines.append(
            f"Signal: {sig.get('velocity_label', '?')} velocity, "
            f"confidence={sig.get('signal_confidence', 0):.2f}"
        )

    bench_items = []
    for stack, info in bench.items():
        if isinstance(info, dict):
            n = info.get("available_engineers", 0)
        else:
            try:
                n = int(info)
            except (TypeError, ValueError):
                n = 0
        bench_items.append(f"{stack}={n}")
    if bench_items:
        lines.append(f"Bench capacity: {', '.join(bench_items)}")

    banned = gt.get("banned_phrases", [])
    if banned:
        lines.append(f"Task banned phrases: {', '.join(banned)}")

    lines.append(f"\nEmail draft:\n{task.get('candidate_output', '')}")
    lines.append("\nVerdict (PASS or FAIL):")
    return "\n".join(lines)


def run_qwen_judge(tasks: list[dict], model, tokenizer, label: str) -> list[dict]:
    import torch

    print(f"  [{label}] judging {len(tasks)} tasks...", flush=True)
    results = []

    for i, task in enumerate(tasks):
        if (i + 1) % 10 == 0:
            print(f"    {i + 1}/{len(tasks)}", flush=True)
        try:
            prompt_msgs = [
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": _format_judge_input(task)},
            ]
            device = next(model.parameters()).device
            inputs = tokenizer.apply_chat_template(
                prompt_msgs,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            ).to(device)

            with torch.no_grad():
                out = model.generate(
                    inputs,
                    max_new_tokens=8,
                    do_sample=False,
                    temperature=1.0,
                    pad_token_id=tokenizer.eos_token_id,
                )
            verdict_raw = tokenizer.decode(
                out[0][inputs.shape[-1]:], skip_special_tokens=True
            ).strip()

            upper = verdict_raw.upper()
            # "FAIL" wins on tie / ambiguity (conservative judge)
            passed = ("PASS" in upper) and ("FAIL" not in upper)

            results.append({
                "task_id": task["task_id"],
                "category": task.get("metadata", {}).get("category", ""),
                "difficulty": task.get("metadata", {}).get("difficulty", ""),
                "passed": passed,
                "expected_pass": task.get("expected_pass"),
                "verdict_raw": verdict_raw,
                "scored_by": label,
            })
        except Exception as exc:
            print(f"    [warn] {task.get('task_id')} error: {exc}", file=sys.stderr)
            results.append({
                "task_id": task["task_id"],
                "passed": False,
                "expected_pass": task.get("expected_pass"),
                "verdict_raw": f"ERROR: {exc}",
                "scored_by": label,
            })

    return results


def load_qwen(hf_repo: str | None, adapter_path: str | None, load_adapter: bool):
    """Load Qwen backbone, optionally with LoRA adapter via Unsloth or plain transformers."""
    # Read base model name from training artifacts
    for hp_path in [ROOT / "training" / "hyperparams.json", ROOT / "hyperparams.json"]:
        if hp_path.exists():
            base_model = json.loads(hp_path.read_text()).get("model", "Qwen/Qwen2.5-0.5B-Instruct")
            break
    else:
        base_model = "Qwen/Qwen2.5-0.5B-Instruct"

    print(f"  Base model: {base_model}", flush=True)

    try:
        from unsloth import FastLanguageModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=base_model,
            max_seq_length=512,
            load_in_4bit=False,
            dtype=None,
        )
        if load_adapter:
            repo = hf_repo or adapter_path or "marthaket/tenacious-judge-orpo-qwen"
            print(f"  Loading LoRA adapter: {repo}", flush=True)
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, repo)
        FastLanguageModel.for_inference(model)

    except ImportError:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.float16,
            device_map="auto" if torch.cuda.is_available() else "cpu",
        )
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        if load_adapter:
            from peft import PeftModel
            repo = hf_repo or adapter_path or "marthaket/tenacious-judge-orpo-qwen"
            print(f"  Loading LoRA adapter: {repo}", flush=True)
            model = PeftModel.from_pretrained(model, repo)
        model.eval()

    return model, tokenizer


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def summary_row(method: str, results: list[dict]) -> dict:
    dr = detection_rate(results)
    labelled = [r for r in results if r.get("expected_pass") is False]
    n_correct = sum(1 for r in labelled if not r["passed"])
    return {
        "method": method,
        "n_tasks": len(labelled),
        "n_correct_fail": n_correct,
        "detection_rate": round(dr, 4),
    }


def print_table(rows: list[dict]) -> None:
    print(f"\n  {'Method':<22}  {'n':>4}  {'correct':>7}  {'det_rate':>10}")
    print("  " + "-" * 48)
    for r in rows:
        print(f"  {r['method']:<22}  {r['n_tasks']:>4}  {r['n_correct_fail']:>7}  {r['detection_rate']:>10.4f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Tenacious-Bench v0.1 ablation runner")
    parser.add_argument(
        "--partition",
        default=str(ROOT / "tenacious_bench_v0.1" / "held_out.jsonl"),
        help="Path to evaluation partition (default: held_out.jsonl)",
    )
    parser.add_argument("--no-llm", action="store_true", help="Skip Claude LLM baseline")
    parser.add_argument("--no-orpo", action="store_true", help="Skip ORPO/Qwen judge")
    parser.add_argument("--hf-repo", default=None, help="HuggingFace repo for ORPO adapter")
    parser.add_argument("--adapter-path", default=None, help="Local path to LoRA adapter")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument(
        "--output",
        default=str(ROOT / "ablation_results.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    tasks = load_tasks(Path(args.partition))
    labelled = [t for t in tasks if t.get("expected_pass") is False]
    print(f"Tenacious-Bench v0.1 ablations | partition: {Path(args.partition).name}")
    print(f"  Total tasks: {len(tasks)} | labelled (expected_pass=False): {len(labelled)}")

    all_results: dict[str, list[dict]] = {}

    # 1 — Deterministic
    print("\n[1/4] Deterministic (hard-gate + heuristic rubric)")
    all_results["deterministic"] = run_pipeline_a(tasks, use_llm=False)

    # 2 — Claude LLM baseline
    if not args.no_llm:
        print("\n[2/4] Claude LLM baseline (Week 10 — claude-sonnet-4-6)")
        all_results["claude"] = run_pipeline_a(tasks, use_llm=True)
    else:
        print("\n[2/4] Claude LLM baseline — skipped (--no-llm)")

    # 3 — Qwen judges (need CUDA)
    if not args.no_orpo:
        try:
            import torch

            if not torch.cuda.is_available():
                print(
                    "\n[3/4] Untrained Qwen — skipped (no CUDA detected)\n"
                    "[4/4] ORPO judge     — skipped (no CUDA detected)\n"
                    "      To run Qwen judges: execute on Colab (T4 GPU) or pass --no-orpo\n"
                    "      to generate the partial results file from baselines only."
                )
            else:
                # Untrained Qwen first (Delta B denominator)
                print("\n[3/4] Untrained Qwen baseline (no adapter — Delta B denominator)")
                model, tokenizer = load_qwen(args.hf_repo, args.adapter_path, load_adapter=False)
                all_results["untrained_qwen"] = run_qwen_judge(tasks, model, tokenizer, "untrained_qwen")
                del model

                # ORPO judge
                print("\n[4/4] ORPO judge (LoRA adapter loaded)")
                model, tokenizer = load_qwen(args.hf_repo, args.adapter_path, load_adapter=True)
                all_results["orpo"] = run_qwen_judge(tasks, model, tokenizer, "orpo")
                del model

        except ImportError:
            print(
                "\n[3/4] Untrained Qwen — skipped (torch not installed)\n"
                "[4/4] ORPO judge     — skipped (torch not installed)"
            )
    else:
        print("\n[3/4] Untrained Qwen — skipped (--no-orpo)")
        print("[4/4] ORPO judge     — skipped (--no-orpo)")

    # --- Summary table ---
    print("\n=== Detection Rate Summary ===")
    rows = [summary_row(method, results) for method, results in all_results.items()]
    print_table(rows)

    # --- Deltas with bootstrap CI ---
    deltas: dict[str, dict] = {}

    if "claude" in all_results and "orpo" in all_results:
        delta_a, lo_a, hi_a = paired_bootstrap(
            all_results["claude"], all_results["orpo"], args.bootstrap, args.seed
        )
        deltas["delta_a"] = {
            "label": "ORPO − Claude (Week 10)",
            "value": round(delta_a, 4),
            "ci_95_lo": round(lo_a, 4),
            "ci_95_hi": round(hi_a, 4),
            "significant_p05": lo_a > 0,
            "target_met": delta_a >= 0.03,
        }
        sig = "p<0.05 ✓" if lo_a > 0 else "ns"
        met = " [target met ≥3pp]" if delta_a >= 0.03 else " [target NOT met]"
        print(f"\n  Delta A (ORPO − Claude):         {delta_a:+.4f}  95% CI [{lo_a:+.4f}, {hi_a:+.4f}]  {sig}{met}")

    if "untrained_qwen" in all_results and "orpo" in all_results:
        delta_b, lo_b, hi_b = paired_bootstrap(
            all_results["untrained_qwen"], all_results["orpo"], args.bootstrap, args.seed
        )
        deltas["delta_b"] = {
            "label": "ORPO − Untrained Qwen",
            "value": round(delta_b, 4),
            "ci_95_lo": round(lo_b, 4),
            "ci_95_hi": round(hi_b, 4),
            "significant_p05": lo_b > 0,
        }
        sig = "p<0.05 ✓" if lo_b > 0 else "ns"
        print(f"  Delta B (ORPO − Untrained Qwen): {delta_b:+.4f}  95% CI [{lo_b:+.4f}, {hi_b:+.4f}]  {sig}")

    # --- Write results ---
    output_path = Path(args.output)
    output_data = {
        "seed": args.seed,
        "n_bootstrap_resamples": args.bootstrap,
        "partition": str(args.partition),
        "n_tasks": len(tasks),
        "n_labelled_expected_fail": len(labelled),
        "summary": rows,
        "deltas": deltas,
        "per_task": {method: results for method, results in all_results.items()},
    }
    output_path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(f"\nResults written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
