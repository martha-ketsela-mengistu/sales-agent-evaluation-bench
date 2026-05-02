# Synthesis Memo — Direct Preference Optimization
**Rafailov et al., NeurIPS 2023 (arXiv 2305.18290)**
**Written:** 2026-04-30 | **Author:** Martha Ketsela Mengistu

---

## Paper Summary

Rafailov et al. show that the RLHF objective — maximize a reward model while staying close to a reference policy — can be solved analytically, producing a closed-form expression that relates the optimal policy directly to preference data. This closed form eliminates the need for explicit reward modeling and RL training: instead of fitting a reward model and then running PPO, DPO directly optimizes a binary cross-entropy loss over (chosen, rejected) pairs. The result is a stable, computationally cheap fine-tuning objective that produces comparable alignment improvements to RLHF without requiring a separately maintained reference model at training time (though DPO still uses the reference model log-probabilities to compute the implicit reward ratio). The paper demonstrates on summarization and dialogue tasks that DPO matches or exceeds PPO-RLHF while being significantly simpler to implement.

---

## Application to Tenacious-Bench v0.1

### Where the paper's foundations are applied

**Theoretical grounding for Path B.** The DPO derivation establishes that preference pairs (chosen, rejected) are sufficient to encode a constraint-satisfaction objective without requiring an explicit reward model. This is the theoretical basis for training the Tenacious judge on (rubric-passing output, constraint-violating output) pairs: the trained judge implicitly encodes the Tenacious constraint satisfaction function, matching the DPO setup where the policy learns which outputs a human (or rubric) would prefer.

**Preference pair format.** DPO requires pairs where the chosen output is strictly preferred over the rejected output on the target criterion. Tenacious-Bench pairs are constructed accordingly: rejected outputs are `expected_pass=False` tasks from the training partition (outputs that fail at least one hard gate or score below 3.5 composite); chosen outputs are either `expected_pass=True` tasks or dev-tier model rewrites of rejected outputs that pass the evaluator. The hard binary pass/fail label from the deterministic evaluator enforces the strict preference ordering DPO requires — there is no ambiguity about which output is "chosen."

---

## Specific Disagreement: DPO's Reference Model Requirement Is a Hard Constraint at Colab T4 Scale

The DPO loss requires computing log-probabilities under both the current policy and a frozen reference model (the original, pre-fine-tuned model). This doubles the memory footprint: at training time, two copies of the model must fit — the trainable model and the reference model for computing the KL divergence term.

**The disagreement:** For the backbone sizes available on a free Colab T4 (16 GB VRAM), this doubles the effective model size that must fit. Qwen 3.5 2B in 16-bit LoRA requires approximately 8 GB VRAM; a DPO run would require 16 GB for both the trainable policy and reference policy simultaneously, saturating the T4 before adding optimizer states. In practice this means DPO on Qwen 3.5 2B on a free Colab T4 is borderline: anecdotal reports indicate that even with gradient checkpointing, the T4 OOMs on 2B with DPO's dual-model requirement.

**Evidence from this project:** The constraint is not hypothetical — Unsloth's Qwen 3.5 fine-tuning guide explicitly recommends 16-bit LoRA (not QLoRA 4-bit), and Unsloth's ORPO and SimPO trainers eliminate the reference model requirement entirely, freeing approximately 8 GB VRAM. This is the direct reason Path B uses ORPO as the primary method: the same outcome (preference-aligned constraint judge) without the reference model overhead.

The paper's claim that DPO is "simple and stable" relative to PPO is correct in the regime where a reference model fits in memory. At 16 GB VRAM, DPO's simplicity advantage over PPO does not translate into a practical advantage over reference-free methods.

**Design decision:** ORPO is used as the primary training method; DPO is not used. The DPO framework provides the theoretical grounding (preference pairs → implicit reward → constraint satisfaction), but the implementation departs to a reference-free variant for compute-budget reasons. The ablation table will report whether ORPO's additional loss term produces different calibration than DPO would, but running DPO is deprioritized unless ORPO fails to converge.

---

## Implication for Preference Pair Quality

DPO's convergence properties depend on the margin between chosen and rejected outputs. If the chosen and rejected outputs are nearly identical (same structure, minimal constraint difference), the DPO loss gradient is small and the model updates slowly. For Tenacious-Bench, this is a data-quality risk: a rejected output that fails only on a single banned phrase (e.g., "rockstar") is very similar to a corresponding chosen output, producing a narrow margin. High-margin pairs (rejected output violates signal grounding, chosen output correctly reflects AI maturity 0/3) are more valuable for training.

This motivates filtering preference pairs by margin before training: pairs where the rubric score difference between chosen and rejected is below a threshold (e.g., Δ < 1.0 on the 5-point composite) should be excluded or downweighted. This filtering step is not prescribed by the DPO paper — it is an inference from the loss landscape that emerges from applying DPO to a rubric-scored domain rather than free-form dialogue.

---

## Reference

Rafailov, R., Sharma, A., Mitchell, E., Manning, C. D., Ermon, S., & Finn, C. (2023). Direct Preference Optimization: Your Language Model is Secretly a Reward Model. *NeurIPS 2023*. arXiv:2305.18290.
