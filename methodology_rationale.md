# Methodology Rationale — Path B: Preference-Tuned Judge

**Author:** Martha Ketsela Mengistu | **Date:** 2026-05-01

---

## Path Selection: B — Preference-Tuned Constraint Judge

Path B was selected on the evidence of three Week 10 trace failures that share a
single root cause: the agent cannot detect when its own completed output violates
a constraint it is capable of satisfying on easier variants.

**Trace `b814fe09c1bbfd8a4ec09bf33639d123`** (Deep Cogito Inc., 2026-04-25):
AI maturity 0/3, `insufficient_signal` hiring velocity.  Agent sent "our data
shows Series A/B companies…" — a grounding claim with no basis in the prospect
context.  The generator produced plausible text; no layer caught the violation.

**Trace `1fa7b6b7eff362232c14da5f7bf80f51`** (Deep Cogito Inc., same prospect,
earlier run): identical inputs, different run.  This time the agent wrote "0/3 AI
maturity and weak hiring velocity signals" — honest, but awkward.  Two runs on the
same input produce opposite constraint-adherence outcomes.  This is inconsistency,
not a generation-quality defect.

**Trace `f264ab49fa6cdc6952224d63481da737`** (Atommap Corp, 2026-04-25):
zero open roles, no funding events, no signals of any kind.  The agent sent the
same Seg1 boilerplate regardless.  The generator has no mechanism to detect that
its output is entirely unsupported.

All three failures are *detection* failures: a post-generation filter that can
score completed outputs against the Tenacious rubric would have caught each one.
Path A (retrain the generator) does not address detection.  Path C (process reward
model) is not motivated — failures are localised to the final output, not the
reasoning chain.  Path B (preference-tuned judge) directly addresses the gap.

---

## Training Algorithm: ORPO

ORPO (Hong, Lee, and Thorne, EMNLP 2024) was selected over DPO (Rafailov et al.,
NeurIPS 2023) and SimPO (Meng, Xia, and Chen, NeurIPS 2024) for two reasons:

1. **Memory budget.** DPO requires a frozen reference model alongside the trainable
   policy, saturating 16 GB VRAM on Qwen 3.5 2B.  ORPO eliminates the reference
   model entirely (Hong et al. §3.2), freeing ~8 GB for the optimizer states and
   activations needed for stable 16-bit LoRA on a Colab T4.

2. **Single-pass simplicity.** ORPO folds SFT and preference alignment into one
   training stage.  Prometheus 2 (Kim et al., 2024) demonstrates that a small
   open-weight model trained on explicit (chosen, rejected) pairs with a rubric-
   conditioned prompt achieves GPT-4-level evaluation correlation on specialized
   domains — the same regime as the Tenacious judge.

SimPO is reserved as an ablation if ORPO dev-set kappa falls below 0.75 at step
200.  The primary metric throughout is per-dimension Cohen's kappa on a 30-task
dev sample, not held-out accuracy, to avoid spending the sealed evaluation budget
during training iteration.

---

## Preference-Leakage Prevention

Per Li et al. (2025), the same model family must not generate training data and
judge it.  The to-be-trained backbone is Qwen 3.5.  Chosen rewrites were generated
by `openai/gpt-4o-mini` (confirmed in `training_data/generation_report.json`).
No Qwen-family model appears in the training data generation pipeline.

---

## Training Data Summary

| Field | Value |
|---|---|
| Source | `tenacious_bench_v0.1/train.jsonl` (139 tasks, all `expected_pass=False`) |
| Pairs format | TRL `ORPOTrainer` — `{prompt, chosen, rejected}` in chat-template form |
| Rejected side | Existing `candidate_output` from each failing task |
| Chosen side | Fresh rewrite via `openai/gpt-4o-mini`, hard-gate verified (≤3 retries) |
| Contamination check | Per-pair n-gram check against `held_out.jsonl` during generation |
| Script | `generation_scripts/build_training_data.py` |
| Output | `training_data/orpo_pairs.jsonl` |

---

## Backbone and LoRA Configuration

| Hyperparameter | Value | Rationale |
|---|---|---|
| Backbone | `Qwen/Qwen3.5-0.5B-Instruct` or `1.5B` | Fits T4 16 GB in 16-bit LoRA; 139 pairs motivate small capacity (Prometheus 2 §5 ablation) |
| Precision | 16-bit (bfloat16 / float16) | Per Unsloth Qwen 3.5 guide — QLoRA 4-bit not recommended for this model family |
| LoRA rank | 16 | Standard starting point; reducible to 8 if overfitting |
| LoRA alpha | 32 | 2× rank — standard scaling |
| Target modules | `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj` | Full attention + MLP, consistent with Unsloth defaults |
| Learning rate | 2e-4 | Unsloth Qwen 3.5 recommended default |
| Batch size | 2 × gradient accumulation 4 = effective 8 | T4 memory limit |
| Max epochs | 3 | Expected wall time 30–60 min on T4; kill if loss diverges by step 100 |
| ORPO β | 0.1 | Default from Hong et al.; adjust if chosen/rejected margin is narrow |
| Seed | 42 | Fixed for reproducibility |

---

## Expected Outcomes

- **Delta A target:** ≥3 pp lift on Tenacious-Bench held-out composite score vs
  Week 10 Claude-only baseline, with p < 0.05 on paired bootstrap (2 000 resamples).
- **Delta B:** trained model vs prompt-engineered Qwen 3.5 (same backbone, no
  training).  A negative Delta B is a publishable finding and goes in the blog
  post honestly.
- **Kill switch:** if held-out pass rate after training is below the untrained
  baseline, the adapter is not deployed.
