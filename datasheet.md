# Datasheet for Tenacious-Bench v0.1

**Authors:** Martha Ketsela Mengistu  
**Created:** 2026-04-29  
**Version:** 0.1  
**License:** CC-BY-4.0  
**Language:** English  
**Domain:** B2B sales outreach automation (Tenacious Intelligence Corporation workflow)

---

## Telescopic Overview

Tenacious-Bench v0.1 is a 343-task evaluation benchmark for B2B sales outreach agents. Each task presents an agent with a prospect's hiring signal brief, bench capacity summary, and optional prior conversation thread, and asks: does the agent's candidate output comply with Tenacious's business rules? The benchmark targets six failure modes — bench over-commitment, signal over-claiming, tone drift, ICP misclassification, ghost-company outreach, and scheduling constraint violations — that public benchmarks (including τ²-Bench retail) do not evaluate. Scoring is fully automated: a Python evaluator applies deterministic hard gates (banned phrases, capacity commitments, funding stage mismatches) followed by a five-dimension rubric scored by an LLM judge (Claude Sonnet 4.6) on a 1–5 scale. Pass threshold is composite ≥ 3.5 and zero hard-gate failures. The dataset is partitioned 37%/31%/32% train/dev/held-out with template-aware stratification to prevent company-name leakage across splits.

---

## Periscopic Summary

**Why this benchmark exists.** Week 10 of TRP1 produced a sales conversion engine that passes τ²-Bench at 0.7267 but exhibits consistent failures on Tenacious-specific constraints: committing engineering capacity the bench does not have (PROBE-3-1), misclassifying funding stages (trace b814fe09), and defaulting to cost-arbitrage tone the style guide explicitly bans (PROBE-4-1). These failures are invisible to τ²-Bench because they require domain-specific ground truth (the Tenacious bench summary, style guide, and ICP definition). Tenacious-Bench provides machine-verifiable tests for exactly these failure modes.

**Key design choices and their justifications:**
- *Five-dimension rubric over binary pass/fail:* Captures partial compliance (an output that passes tone but fails signal grounding should score differently from one that fails both).
- *Hard gates short-circuit to composite=0:* Ensures that a single critical violation (e.g., committing unavailable Rust capacity) cannot be masked by high scores on other dimensions.
- *Hybrid deterministic + LLM judge:* Formally specifiable constraints (banned phrases, capacity commitments, word counts) use deterministic checks; semantic dimensions (signal_grounding, icp_accuracy) use LLM scoring. Rationale documented in synthesis memo for Liu et al. (2024).
- *Template-aware partition:* All variants of the same company template stay in one partition, preventing company-name 8-gram leakage across train/held-out.
- *Pass rate ~30%:* Intentionally challenge-weighted. The benchmark is designed to expose failure modes, not to reward adequate performance.

**Known limitations:**
- Trace-derived tasks represent only 3 of 343 tasks (0.9%) — the trace pool had limited email content (18 HTML excerpts) and only one clean (baseline-FAIL, method-PASS) pair for bench-over-commitment. Multi-LLM synthesis (not yet run) is required to reach the target ~25% trace-derived share.
- LLM judge calibration has not been validated against human labels. Inter-rater agreement (30-task hand-label protocol) is pending.
- `scoring_evaluator.py` uses TF-IDF cosine as a proxy for embedding similarity in the contamination check. Sentence-transformer embeddings (e.g., `all-MiniLM-L6-v2`) should replace this before final publication.
- The benchmark covers six of the ten failure categories identified in the audit. Four categories (multi-thread-conflict, company-objection-pivot, SDR-role-confusion, greeting-only-close) are not yet represented.

---

## 1. Motivation

**For what purpose was the dataset created?**  
To evaluate B2B sales outreach agents on Tenacious-specific business rules that public benchmarks do not measure. The immediate purpose is to (a) quantify the failure rate of the Week 10 Conversion Engine on constraint-violation failure modes and (b) provide training signal for a preference-tuned judge (Path B, SimPO/ORPO) that can detect these violations post-generation. The broader purpose is to provide a reusable, machine-verifiable benchmark for any agent operating in the Tenacious sales workflow.

**Who created the dataset and on behalf of which entity?**  
Martha Ketsela Mengistu, TRP1 cohort participant, as part of Week 11 of the TRP1 Challenge. The workflow domain is Tenacious Intelligence Corporation; Tenacious is named only as a workflow context and no private company data is included.

**Who funded the creation of the dataset?**  
TRP1 Challenge program. API costs to date: $0.00 (all tasks generated deterministically or from existing Week 10 artifacts). OpenRouter synthesis and eval-tier scoring (Claude Sonnet 4.6 on held-out slice) are budgeted at $3–5 and $2–3 respectively, not yet spent.

**Any other comments?**  
The dataset is built from limited seed material — 376 agent traces, 30 probe results, and 18 HTML email excerpts from held_out_traces.jsonl — using four authoring modes rather than from a large labeled corpus. This is a feature, not a limitation: the methodology is designed for the no-historical-data scenario common in enterprise AI deployment contexts.

---

## 2. Composition

**What do the instances represent?**  
Each instance is a sales evaluation task. It contains: (1) an `input_context` with a prospect brief (company name, employee count, funding event, hiring signal), bench summary (available engineers per stack), and optional prior conversation thread; (2) a `candidate_output` — a sales agent reply or cold outreach draft; (3) `ground_truth` with banned phrases, required phrases, calendar link requirement, and word count limit; (4) an `evaluator_config` with five rubric dimensions and active hard gates; and (5) `metadata` with category, source mode, difficulty, and creation date.

**How many instances are there?**

| Partition | Count | Share |
|---|---|---|
| train | 126 | 37% |
| dev | 108 | 31% |
| held_out | 109 | 32% |
| **Total** | **343** | 100% |

Category distribution:

| Category | Count | Share |
|---|---|---|
| signal-over-claiming | 113 | 33% |
| bench-over-commitment | 89 | 26% |
| tone-drift | 50 | 15% |
| scheduling-constraint | 31 | 9% |
| ghost-company | 30 | 9% |
| icp-misclassification | 30 | 9% |

Source mode distribution:

| Source mode | Count | Share |
|---|---|---|
| programmatic | 335 | 98% |
| hand-authored | 5 | 1% |
| trace-derived | 3 | 1% |

**Does the dataset contain all possible instances or is it a sample?**  
It is a sample. The programmatic tier covers a structured parameter sweep (8 funding variants × 5 signal variants × 7 bench configurations × 14 company templates = up to 3,920 combinations before deduplication). After deduplication and calibration, 335 unique programmatic tasks remain. The hand-authored tier covers 5 adversarial edge cases. The trace-derived tier covers 3 tasks from `held_out_traces.jsonl` where probe context was fully annotated. Multi-LLM synthesis (target ~25% of final dataset) is not yet run.

**What does each instance consist of?**  
Structured JSON per the Tenacious-Bench v0.1 schema (documented in `schema.json`). All fields are synthetic or derived from public Crunchbase/layoffs.fyi data — no private company data, no individual personal information.

**Is there a label or target associated with each instance?**  
Yes. `expected_pass` (boolean) is the primary label. It is set by the deterministic evaluator (`scoring_evaluator.py --no-llm`) during dataset construction — not by human annotation. A secondary label, `metadata.difficulty` (easy/medium/hard), is assigned during construction based on signal confidence and parameter values.

**Is any information missing from individual instances?**  
Tasks from the ghost-company and scheduling-constraint categories have sparse `hiring_signal_brief` fields (low or absent funding signals) by design — these categories test agent behavior when signal is insufficient, so the sparsity is intentional.

**Are there recommended data splits?**  
Yes: train (50% target, 37% actual), dev (30%), held_out (20%/32%). The split is template-aware: all variants of a given company template reside in one partition. The held_out partition is gitignored from training scripts and should remain sealed until leaderboard publication.

**Are there errors, sources of noise, or redundancies?**  
The `expected_pass` labels are set by the deterministic evaluator. Tasks where the LLM judge (full scoring) would disagree with the deterministic scorer are not yet identified — this requires the inter-rater agreement protocol to complete. The deterministic scorer is conservative on `signal_grounding` and `icp_accuracy` (defaults to score=3 for both), which may under-score passing outputs.

**Is the dataset self-contained?**  
Yes. All inputs are embedded in the JSONL files. No external URLs are fetched at evaluation time. The `bench_summary` values in each task are embedded directly rather than referenced from the live `bench_summary.json`.

**Does the dataset contain confidential or sensitive data?**  
No. All company names, domains, and funding figures are either synthetic (AlphaStack Inc, GoServices Ltd, etc.) or derived from probe library templates that use fictionalised names. No real prospects, no individual personal data.

---

## 3. Collection Process

**How was the data acquired?**  
Four authoring modes:

1. **Trace-derived (1%):** Real Week 10 agent email outputs extracted from `held_out_traces.jsonl`. HTML stripped to plain text. Input context reconstructed from `probe_library.md` probe inputs and `bench_summary.json`. Ground truth derived from probe category and failure mode.

2. **Programmatic (98%):** Combinatorial parameter sweep over 14 company templates × 8 funding variants × 5 signal variants × 7 bench configurations. Candidate outputs selected from category-specific failing/passing template pools. `expected_pass` calibrated by deterministic evaluator post-generation.

3. **Multi-LLM synthesis (0%, pending):** Not yet executed. Will use OpenRouter (Qwen3-Next-80B-A3B or DeepSeek V3.2) to generate candidate outputs from probe inputs. Output will be judge-filtered (Pipeline B, pointwise scoring) before inclusion. Model family rotation policy documented in `methodology.md` to prevent preference leakage (Li et al., 2025).

4. **Hand-authored adversarial (1%):** Five tasks written to cover edge cases the automated pipeline cannot generate: boundary-condition funding dates (exactly 180 days ago), vague quantity phrases that evade hard gates, word-count boundary cases (118 vs 122 words), and low-confidence over-claiming where the stage label is correct but assertion strength is not.

**What mechanisms or procedures were used to collect data?**  
- `generation_scripts/build_dataset.py` (reproducible, seeded with `--seed 42`)
- `scoring_evaluator.py --no-llm` for `expected_pass` calibration
- `generation_scripts/contamination_check.py` for partition validation

**Who was involved in the data collection process?**  
One person (Martha Ketsela Mengistu). No crowdworkers. No external annotators for this version.

**Over what timeframe was the data collected?**  
2026-04-29. All synthetic tasks created on a single day. Trace-derived tasks draw on Week 10 probe runs (2026-04-24/25).

**Were any ethical review processes conducted?**  
Not applicable — all data is synthetic and describes no real individuals or companies.

---

## 4. Preprocessing, Cleaning, and Labeling

**Was any preprocessing done?**  
Yes:
- HTML tags stripped from trace-derived email excerpts using `re.sub(r"<[^>]+>", " ", html)`.
- Near-duplicate tasks removed by input-field 5-gram Jaccard deduplication (threshold 0.6) during dataset construction.
- `expected_pass` labels recalibrated from aspirational category-logic values to deterministic evaluator scores, correcting 73 labels (21% of total tasks).

**Was raw data saved?**  
Yes. The pre-deduplication programmatic task pool (2,808 tasks) is reproducible by running `build_dataset.py` with the same seed and inspecting before the dedup step. The `generation_scripts/` directory contains all generation code.

**Is the software used to preprocess available?**  
Yes: `generation_scripts/build_dataset.py` and `generation_scripts/contamination_check.py` in this repository.

---

## 5. Uses

**Has the dataset been used for any tasks already?**  
Tenacious-Bench v0.1 is used in Week 11 of TRP1 to:
1. Establish a baseline score for the Week 10 Conversion Engine (held-out evaluation, pending).
2. Provide (chosen, rejected) preference pairs for Path B training (SimPO/ORPO judge fine-tuning, pending).

**What other tasks could the dataset be used for?**  
- Evaluating any B2B sales outreach LLM agent on constraint-following behavior.
- Training a rejection-sampling layer that filters agent outputs before delivery.
- Studying the relationship between signal confidence and appropriate language register in sales contexts.
- Benchmarking prompt-engineering interventions against trained adapters (Delta B measurement).

**Are there tasks for which the dataset should NOT be used?**  
- As a general-purpose sales email quality dataset: Tenacious-Bench is designed around Tenacious-specific business rules (Style Guide v2, bench capacity constraints, ICP definition). It should not be used to evaluate agents operating under different sales policies.
- As a proxy for human judgment on sales effectiveness: the benchmark tests constraint compliance, not conversion rate. High benchmark scores do not predict booking rates.
- For fine-tuning a generation model to produce Tenacious-style emails for any real prospecting without human review: the candidate outputs in the training partition include intentionally failing examples (pass rate ~30%).

**Anything about composition that might impact future uses?**  
The programmatic tier (98% of tasks) uses a small set of company name templates repeated across parameter sweeps. A model fine-tuned on this dataset may overfit to these company names. Future versions should replace or extend the template pool.

---

## 6. Distribution

**Will the dataset be distributed to third parties?**  
Yes. Train and dev partitions will be published to HuggingFace Hub under the handle `martha-ketsela-mengistu/tenacious-bench-v0.1`. The held-out partition will be published after the leaderboard is closed.

**How will the dataset be distributed?**  
HuggingFace Hub dataset repository. Three JSONL files (`train.jsonl`, `dev.jsonl`, `held_out.jsonl`) plus `manifest.json`, `datasheet.md`, `contamination_report.json`, and `scoring_evaluator.py`. A quickstart example will be included in `README.md`.

**When will the dataset be distributed?**  
Public release planned for 2026-05-03 (after Friday final submission) pending program staff sign-off per the publication checklist.

**Under what license?**  
CC-BY-4.0. Attribution: "Tenacious-Bench v0.1, Martha Ketsela Mengistu, TRP1 Challenge Week 11, 2026."

**Have any third parties imposed IP restrictions?**  
No. All inputs are synthetic. The Tenacious workflow domain is referenced by name for context only; no proprietary Tenacious data (real prospect lists, real pricing, real client information) is included.

---

## 7. Maintenance

**Who will support, host, and maintain the dataset?**  
Martha Ketsela Mengistu (martha@10academy.org) during TRP1 and for a reasonable period after. Long-term hosting via HuggingFace Hub (persistent URL, versioned).

**How can the curator be contacted?**  
martha@10academy.org, or via the HuggingFace dataset discussion board.

**Is there an erratum?**  
Not at v0.1. Errors discovered after publication will be documented in a GitHub Issues tracker linked from the HuggingFace dataset card.

**Will the dataset be updated?**  
Planned updates:
- **v0.2:** Multi-LLM synthesis tier added (~75 tasks); inter-rater agreement labels incorporated; missing failure categories (multi-thread-conflict, company-objection-pivot) added.
- **v0.3:** Held-out partition refreshed after leaderboard close to prevent saturation.

**Will older versions continue to be hosted?**  
Yes. HuggingFace Hub supports versioned datasets. v0.1 will remain accessible after v0.2 is published.

**Is there a mechanism for others to contribute?**  
Not for v0.1. Contributions (additional hand-authored adversarial tasks, rubric corrections) may be submitted via pull request to the GitHub repository after the TRP1 final submission date. Contributions will be validated against `scoring_evaluator.py` and reviewed by the curator before inclusion.

---

## Microscopic Detail — Schema and Scoring

### Task schema fields

| Field | Type | Description |
|---|---|---|
| `task_id` | string | Unique identifier, e.g. `TEN-BOC-001` |
| `version` | string | Schema version (`"0.1"`) |
| `probe_id` | string or null | Source probe from Week 10 library, if trace-derived |
| `description` | string | Human-readable description of the test scenario |
| `input_context.prospect_brief` | object | Company name, domain, employee count, funding event, hiring signal brief |
| `input_context.bench_summary` | object | Available engineers per stack at time of outreach |
| `input_context.prior_thread` | array | Prior conversation turns (empty for cold outreach) |
| `candidate_output` | string | The agent output to be evaluated |
| `ground_truth.banned_phrases` | array | Phrases that must not appear in the output |
| `ground_truth.required_phrases` | array | At least one must appear for a passing signal_grounding score |
| `ground_truth.require_calendar_link` | boolean | Whether a booking link is required (true for cold outreach) |
| `ground_truth.max_word_count` | integer or null | Word count ceiling (120 cold, 200 warm, 100 re-engagement) |
| `evaluator_config.hard_gates` | array | Active gate names for this task |
| `evaluator_config.rubric` | array | Five dimension objects with `dimension`, `weight`, `criteria` |
| `pass_threshold` | number | `3.5` (composite score on 1–5 scale) |
| `expected_pass` | boolean | Label set by deterministic evaluator calibration |
| `metadata.category` | string | One of six failure categories |
| `metadata.source_mode` | string | `trace-derived`, `programmatic`, `hand-authored` |
| `metadata.difficulty` | string | `easy`, `medium`, `hard` |

### Rubric dimensions

| Dimension | Weight | Hard gate? | Scoring anchor |
|---|---|---|---|
| `tone_adherence` | 0.30 | Yes — any global banned phrase or external "bench" word → score 1 | 1 = CTO-visible violation; 5 = matches Style Guide v2 GOOD example |
| `signal_grounding` | 0.30 | Yes — funding stage mismatch → score 1 | 1 = fabricated or wrong stage; 5 = all claims grounded in input_context |
| `bench_honesty` | 0.20 | Yes — zero-stack commitment → score 1 | 1 = commits unavailable capacity; 5 = correctly routes to delivery lead |
| `icp_accuracy` | 0.10 | No | 1 = wrong segment language; 5 = precise to company profile |
| `completeness` | 0.10 | No | 1 = missing required element (calendar link, next step); 5 = all elements present |

### Contamination check results (v0.1)

| Check | Method | Threshold | Violations |
|---|---|---|---|
| N-gram overlap | 8-gram Jaccard on scenario-specific input fields | Jaccard > 0.15 | 0 |
| Embedding similarity | TF-IDF cosine (1–3 gram, sublinear_tf) | Cosine > 0.85 | 0 |
| Time-shift | Funding dates: past and within 3-year window | Any future or >3yr date | 0 |

*Note: TF-IDF cosine is a proxy. Sentence-transformer embedding check (all-MiniLM-L6-v2) is planned before final HuggingFace push.*

---

## References

- Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H., Daumé III, H., & Crawford, K. (2021). Datasheets for datasets. *Communications of the ACM*, 64(12), 86–92. arXiv:1803.09010.
- Pushkarna, M., Zaldivar, A., & Kjartansson, O. (2022). Data Cards: Purposeful and Transparent Dataset Documentation for Responsible AI. *ACM FAccT 2022*. arXiv:2204.01075.
- Liu, R. et al. (2024). Best Practices and Lessons Learned on Synthetic Data for Language Models. *COLM 2024*. arXiv:2404.07503.
- Chen, S. et al. (2025). Recent Advances in Large Language Model Benchmarks against Data Contamination: From Static to Dynamic Evaluation. *EMNLP 2025*. arXiv:2502.17521.
