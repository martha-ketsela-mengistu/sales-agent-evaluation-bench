# Methodology Declaration — Tenacious-Bench v0.1

**Declared:** 2026-04-29
**Training Path:** B — Preference-tuned judge/critic (SimPO or ORPO)

---

## Path Selection Justification

The dominant failure pattern in Week 10 is **inconsistency**: the agent produces acceptable outputs when signal is clear but violates constraints when signal is ambiguous or overridden. This is not a generation-quality failure (Path A) and not a trajectory-planning failure (Path C). It is a failure to detect when the agent's own completed output violates a constraint it can satisfy in isolation.

**Evidence from Week 10 traces:**

- **Trace `b814fe09c1bbfd8a4ec09bf33639d123`** (Deep Cogito Inc., 2026-04-25): AI maturity score 0/3, hiring velocity `insufficient_signal`, yet agent sent email with framing "our data shows Series A/B companies…" — no grounding in the prospect's actual signal. The generator produced a plausible email; no layer caught the grounding violation.
- **Trace `1fa7b6b7eff362232c14da5f7bf80f51`** (Deep Cogito Inc., same prospect, earlier run): same 0/3 AI maturity, different email wording ("our data shows… 0/3 AI maturity and weak hiring velocity signals"), which is honest but awkward. Two runs, same input, different constraint adherence — inconsistency across runs, not a single generation failure.
- **Trace `f264ab49fa6cdc6952224d63481da737`** (Atommap Corp, 2026-04-25): zero open roles, no funding events, no signals of any kind. Same Seg1 boilerplate email sent regardless. The generator is unaware that its output is unsupported.
- **PROBE-3-1** (Bench Over-Commitment, FAILED): agent failed to disclaim Rust unavailability even though `bench_summary.json` is in context. The capability to reference the bench exists (passing traces do reference it); the trigger detection does not.
- **PROBE-8-2, PROBE-8-3** (Scheduling, FAILED) vs **PROBE-8-1** (Scheduling, PASSED): same scenario category, different difficulty variant. The agent handles the simple case but drops the timezone constraint on harder variants. τ²-Bench would not catch this; the failure is in consistency across difficulty, not in task completion.

**Why Path B (judge/critic):** A trained judge/critic deployed as a rejection-sampling layer can catch constraint violations in completed agent outputs before they are returned. It does not replace the generator — it acts as a post-generation filter. The (chosen, rejected) training pairs come directly from pass/fail probe pairs: failing outputs (rejected) versus hand-corrected or rubric-passing outputs (chosen). This maps naturally onto SimPO or ORPO, which are reference-free and fit a Colab T4 without a reference model copy.

**Rejected alternatives:**

- Path A (SFT): Tone and generation quality are acceptable on easy variants. The problem is not output quality — it is that the agent cannot tell when its output violates a constraint. Retraining the generator does not address the detection failure.
- Path C (PRM): No evidence of trajectory-level failures where individual steps were locally correct but globally the plan failed. Failures are localized to the final output, not the reasoning chain.

---

## Supporting Literature

1. Meng, Xia, and Chen (2024). *SimPO: Simple Preference Optimization with a Reference-Free Reward.* NeurIPS 2024. — Reference-free objective; directly applicable to training a constraint-violation detector without a reference model, reducing VRAM requirement to fit Colab T4.
2. Hong, Lee, and Thorne (2024). *ORPO: Monolithic Preference Optimization without Reference Model.* EMNLP 2024. — Alternative reference-free method; to be compared against SimPO in ablation.
3. Kim et al. (2024). *Prometheus 2: An Open-Source Language Model Specialized in Evaluating Other Language Models.* — Canonical reference for training a small open judge from preference data; training procedure directly adapted for the Tenacious judge.
4. Rafailov et al. (2023). *Direct Preference Optimization.* NeurIPS 2023. — Foundational algorithm; provides the theoretical basis that preference training on (chosen, rejected) pairs can encode constraint satisfaction.

---

## Planned Implementation

- **Backbone:** Qwen 3.5 0.8B or 2B (fits Colab T4 in 16-bit LoRA per Unsloth Qwen 3.5 guide)
- **Framework:** Unsloth + TRL `ORPOTrainer` or `CPOTrainer` (SimPO)
- **Training data source:** Pass/fail pairs extracted from probe runs in `week10_data/trace_log.jsonl` (376 traces; email-generation spans provide the richest signal)
- **Preference pair format:** `(chosen: rubric-passing output, rejected: constraint-violating output)` — rejections from probe failures; chosen outputs from hand-correction or dev-tier model rewrite using a different model family than the judge (preference leakage prevention per Li et al., 2025)
- **Deployment:** Post-generation filter wrapping the Week 10 email composer; returns the highest-scoring candidate from N=3 rejection samples

---

## Open Questions (resolve before Day 2)

- [ ] SimPO vs ORPO final choice: run 10-step test on T4 to confirm memory budget; ORPO is slightly simpler to implement with TRL, SimPO typically shows better calibration on constraint tasks
- [ ] Confirm rejection N (3 or 5 candidates) against latency budget — 3 candidates adds ~2× base latency
- [ ] Verify Unsloth supports Qwen 3.5 (not Qwen 2.5) without custom patches
