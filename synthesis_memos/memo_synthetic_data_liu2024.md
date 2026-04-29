# Synthesis Memo — Best Practices and Lessons Learned on Synthetic Data for Language Models
**Liu et al., COLM 2024 (arXiv 2404.07503)**
**Written:** 2026-04-29 | **Author:** Martha Ketsela Mengistu

---

## Paper Summary

Liu et al. provide a broad survey of synthetic data use in language model training and evaluation. Their core prescriptions for dataset authoring are: (1) validate synthetic outputs through executable testing or symbolic verification engines; (2) combine synthetic data with real-world data rather than using synthetic alone; (3) use complexity and diversity scaling (e.g., Evol-Instruct) to avoid over-simplified scenarios; and (4) maintain protected in-house evaluation benchmarks to prevent leakage. They warn explicitly that "low-fidelity synthetic human preference data might be limited in accurately reflecting nuanced human judgment," and that purely synthetic rephrasing renders token-level decontamination ineffective.

---

## Application to Tenacious-Bench v0.1

### Where the paper's prescriptions are followed

**Multi-source mixing.** The paper recommends combining real and synthetic data. Tenacious-Bench uses a four-mode authoring pipeline: ~30% trace-derived (real Week 10 agent outputs), ~30% programmatic, ~25% multi-LLM synthesis, and ~15% hand-authored adversarial. The trace-derived tier provides the "real" grounding the paper calls for; the synthetic tiers provide scale and coverage of edge cases the traces alone cannot reach.

**Protected evaluation.** The paper prescribes maintaining sealed held-out evaluation benchmarks. Tenacious-Bench seals 20% of tasks in `held_out.jsonl`, gitignored from training scripts, consistent with this recommendation.

**Diversity scaling.** The programmatic tier varies inputs across a combinatorial sweep (funding stage, bench availability, signal_confidence, days_ago, open_roles) to avoid the "over-simplified scenarios" the paper warns against. A single PROBE-3-1 bench-over-commitment scenario becomes ~15 distinct tasks by varying stack availability and prior thread context.

---

## Specific Disagreement: Symbolic Verification vs. LLM-as-Judge for Quality Filtering

The paper's strongest quality-control prescription is: *"validate correctness through symbolic engines or executable testing"* (citing AlphaGeometry as the exemplar). The implicit assumption is that the correctness criterion for a synthetic task is formally specifiable — a proof is correct if it verifies; a code solution is correct if it passes tests.

**The disagreement:** For Tenacious-Bench, this prescription only partially applies, and forcing it universally would reduce dataset quality.

The five rubric dimensions split into two categories:

- **Formally specifiable (symbolic/deterministic checks are correct):** `tone_adherence` (banned phrase membership), `bench_honesty` (capacity commitment against `bench_summary` values), and `completeness` (calendar link presence, word count). These hard gates are implemented as exact string matching and regex — they are symbolic verification in the paper's sense.

- **Not formally specifiable:** `signal_grounding` (does the output accurately reflect the prospect's signal mix?) and `icp_accuracy` (is the framing appropriate for this company's stage and maturity?). These require semantic reasoning about factual accuracy and contextual fit. There is no symbolic engine that can verify whether an outreach email correctly characterizes a company's AI maturity score.

The paper's prescription to prefer symbolic verification would, if applied universally to Tenacious-Bench, force us to either (a) reduce the rubric to only the symbolically checkable dimensions (abandoning signal_grounding and icp_accuracy entirely) or (b) treat LLM judge scores as second-class. Neither is correct.

**Evidence from Week 10:** Trace `b814fe09c1bbfd8a4ec09bf33639d123` (Deep Cogito Inc.) shows the agent sending "our data shows Series A/B companies…" to a prospect with AI maturity 0/3 and `insufficient_signal` hiring velocity. The violation is a grounding failure, not a banned-phrase failure. No symbolic checker can catch it — it requires knowing the prospect's actual signal state and comparing it to the claim. This is precisely the class of failure that necessitates the LLM judge.

**Design decision:** Tenacious-Bench uses a hybrid: deterministic hard gates for formally specifiable constraints, LLM-as-judge (claude-sonnet-4-6) for semantic dimensions. The paper does not address this hybrid pattern. The disagreement is that symbolic verification cannot be the universal standard for a domain where some correctness criteria are inherently semantic.

---

## Implication for Contamination Protocol

The paper warns that "synthetic rephrasing renders token-level decontamination ineffective." This directly informs the three-check contamination protocol in Tenacious-Bench: n-gram overlap alone (token-level) is insufficient; embedding cosine similarity is required as the second check to catch paraphrased duplicates. The paper's warning is the justification for why the contamination check cannot stop at n-gram matching.

---

## Reference

Liu, R., Wei, J., Liu, F., Si, C., Zhang, Y., Rao, J., Zheng, S., Peng, D., Yang, D., Zhou, D., & Dai, A. M. (2024). Best Practices and Lessons Learned on Synthetic Data for Language Models. *Conference on Language Modeling (COLM 2024)*. arXiv:2404.07503.
