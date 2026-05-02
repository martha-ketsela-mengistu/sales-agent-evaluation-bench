# Synthesis Memo — Recent Advances in LLM Benchmarks against Data Contamination
**Chen et al., EMNLP 2025**
**Written:** 2026-04-30 | **Author:** Martha Ketsela Mengistu

---

## Paper Summary

Chen et al. survey the evolution of contamination-prevention strategies in LLM benchmarks from static to dynamic evaluation. They categorize the contamination problem into three types: (1) direct contamination, where benchmark tasks appear verbatim in training corpora; (2) paraphrase contamination, where rephrased versions of test inputs exist in pretraining; and (3) solution contamination, where ground-truth outputs or answer keys are exposed. Their empirical analysis shows that n-gram-based decontamination — the method used in most current benchmarks — catches only direct contamination; paraphrase contamination evades it. The paper's central prescription is a shift from *static* benchmarks (fixed task pools that are repeatedly evaluated) to *dynamic* evaluation (task pools that are refreshed, parameterized, or generated on-the-fly). Dynamic evaluation prevents contamination by design because new task instances are generated after any candidate model's training cutoff.

---

## Application to Tenacious-Bench v0.1

### Where the prescriptions are followed

**Multi-check contamination protocol.** The paper's finding that n-gram matching alone is insufficient is the direct motivation for `contamination_check.py`'s three-check protocol: n-gram 8-gram overlap (catches direct contamination), TF-IDF cosine similarity below 0.85 (catches paraphrase contamination), and time-shift verification (catches contamination through stale public-data references). This three-check design implements the paper's recommendation to layer detection methods.

**Time-stamped grounding.** The paper's time-shift concern — that tasks referencing public events can become contaminated when those events enter pretraining corpora — is addressed by requiring all funding events in Tenacious-Bench inputs to have `closed_at` within a documentable window. Any task referencing a funding event is verified against the event date and the task creation date.

**Sealed held-out partition.** The paper recommends that held-out partitions be withheld from the public until after evaluation runs are complete. `held_out.jsonl` is listed in `.gitignore` relative to training scripts, consistent with this recommendation.

---

## Specific Disagreement: Fully Dynamic Evaluation Is Incompatible with Benchmark Reproducibility

Chen et al.'s primary prescription is that benchmarks should move toward fully dynamic evaluation: generating new task instances at evaluation time, using parametric templates or on-the-fly LLM synthesis, so that no fixed task pool exists for models to memorize. They cite PromptBench and DynaBench as exemplars.

**The disagreement:** For Tenacious-Bench, fully dynamic evaluation would destroy the reproducibility guarantee that is the point of having a benchmark.

The value of Tenacious-Bench is not just that it tests agents — it is that it produces stable, comparable scores across agent versions, training runs, and time. Delta A (trained model vs. Week 10 baseline) requires that both evaluations be run on the *same fixed tasks*. Delta B (trained model vs. prompt-engineered baseline) requires the same. If held-out tasks are regenerated at each evaluation call, a 2-point improvement in Delta A could be attributable to task variation rather than training lift. The entire ablation table loses interpretability.

**The paper's own evidence qualifies this.** Chen et al. acknowledge that "static benchmarks remain necessary for reproducibility-critical evaluations" (Section 4.2). Their dynamic-evaluation recommendation targets large-scale evaluation against foundation models, where task pool size is sufficient to subsample fresh instances without affecting aggregate statistics. Tenacious-Bench has 59 held-out tasks — far below the size where subsampling would produce stable aggregate statistics.

**Design decision:** Tenacious-Bench uses a static sealed held-out partition. Contamination is prevented not by dynamic generation but by (a) the three-check protocol that verifies held-out tasks cannot be memorized from training data, (b) the time-shift verification, and (c) the restriction that held-out tasks are never committed to any public-facing branch until after the leaderboard is published. The paper's prescription is correct for large-scale foundation model evaluation; it does not apply at the scale of a 59-task held-out partition where reproducibility is the binding constraint.

---

## Implication for Solution Contamination in Preference-Pair Training

The paper's solution-contamination category is the most directly relevant to Path B training. If the (chosen, rejected) preference pairs in `training_data/` are derived from tasks in `held_out.jsonl` — even indirectly, by using similar prompts to generate chosen outputs — the trained judge would be contaminated with information about the held-out tasks' ground-truth rubric application. This is a version of solution contamination that the paper identifies but does not resolve for the synthetic-benchmark-as-training-data case.

**Mitigation already in place:** Preference pairs are sourced exclusively from the training partition (50%) and dev partition (30%). The held-out partition is not used in training data preparation. Chosen outputs are generated by dev-tier models using the Week 10 probe corrections as seeds — a different generation process than the judge scoring pipeline. This separation prevents solution leakage by ensuring that the training signal for the judge does not encode information about held-out scoring decisions.

---

## Reference

Chen, H., Zhao, H., Song, X., Xu, F. F., Mi, F., Wang, S., & Li, J. (2025). Recent Advances in Large Language Model Benchmarks against Data Contamination: From Static to Dynamic Evaluation. *EMNLP 2025*.
