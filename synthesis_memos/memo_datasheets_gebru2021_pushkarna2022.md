# Synthesis Memo — Datasheets for Datasets + Data Cards
**Gebru et al., 2021 (arXiv 1803.09010) + Pushkarna et al., FAccT 2022**
**Written:** 2026-04-30 | **Author:** Martha Ketsela Mengistu

---

## Paper Summaries

**Datasheets for Datasets (Gebru et al.)** proposes that every dataset ship with a standardized documentation artifact modeled after hardware component datasheets. The template covers seven sections: motivation (why the dataset was created), composition (what the data represents), collection process (how it was gathered), preprocessing/cleaning/labeling (transformations applied), uses (intended and inappropriate uses), distribution (how and under what terms), and maintenance (ongoing curation plans). The central argument is that undocumented datasets enable misuse and mask harmful representation failures; explicit documentation forces creators to surface choices that are otherwise invisible.

**Data Cards (Pushkarna et al.)** extends Datasheets with a layered architecture. They introduce three levels of detail: *telescopic* (a single-page summary for quick intake decisions), *periscopic* (contextual detail on intended use, known gaps, and prior evaluations), and *microscopic* (full technical provenance for reproducibility). Their empirical study found that practitioners consult different layers at different decision points: business stakeholders read telescopic, researchers read periscopic, engineers working on integration read microscopic.

---

## Application to Tenacious-Bench v0.1

### Where the prescriptions are followed

**All seven Gebru sections are addressed in `datasheet.md`.** Motivation names the τ²-Bench gap for B2B sales evaluation. Composition documents the four-mode authoring pipeline and the six failure categories with counts. Collection process names the seed corpus (Style Guide v2, Week 10 traces, Crunchbase sample). Preprocessing names the three contamination checks. Uses explicitly names inappropriate use (re-training a general outreach generator without domain adaptation). Distribution specifies CC-BY-4.0. Maintenance identifies that v0.2 should address failure modes named in the skeptic's appendix.

**Pushkarna's layering is implemented.** `datasheet.md` opens with a one-page telescopic summary (dataset name, task count, evaluation target, baseline score, license). The periscopic layer covers known gaps, labeling quality, and prior-evaluation context. The microscopic layer provides per-field schema documentation and contamination check parameters.

---

## Specific Disagreement: The Datasheets Template Assumes Historical Collection, Not Synthetic Generation

Both papers' collection-process section assumes the dataset was gathered from a pre-existing source — the questions are "how was data collected?" and "what mechanisms were used to collect it?" (Gebru §3). The implicit model is: data exists in the world, a collector samples it, and the datasheet documents the sampling procedure.

**The disagreement:** This framing is architecturally wrong for synthetically authored benchmarks. For Tenacious-Bench, there is no pre-existing source to sample from. The collection process is generative: a multi-LLM pipeline authors tasks that did not exist before the dataset was built. Applying the Gebru collection-process template naively produces documentation that answers "what prompts were sent to OpenRouter" — accurate but incomplete and misleading about the nature of the artifact.

The relevant question for a synthetic benchmark is not *how was data collected* but *how was data quality controlled*: what authoring modes were used, what judge criteria were applied, what deduplication thresholds were set, and what ground-truth labels were derived by what method. None of these map cleanly onto Gebru's collection-process questions.

**Evidence from this project:** The four authoring modes (trace-derived, programmatic, multi-LLM synthesis, hand-authored) all involve different quality-control processes — trace-derived tasks are validated by the deterministic evaluator against real trace IDs; programmatic tasks are deduped against a combinatorial explosion limit; synthesis tasks pass a three-dimension judge filter; hand-authored tasks are reviewed manually. Gebru's "was an IRB approval obtained?" question is not applicable. Pushkarna's "what is the data provenance?" question cannot be answered with a data source URL.

**Design decision:** `datasheet.md` preserves all seven Gebru sections but replaces the collection-process section's source-sampling framing with an *authoring-pipeline* framing: mode rationale, model routing, quality-gate parameters, and labeling provenance. This is a substantive departure from both templates and is justified by the fact that synthetic benchmark construction is a different epistemic activity than dataset collection.

---

## Implication for Distribution and Maintenance

Gebru's distribution section asks about legal restrictions on sharing. For synthetic benchmarks derived from proprietary inputs (Tenacious Style Guide, internal bench summaries), the relevant restriction is not IP law on the data but disclosure risk: does publishing task inputs reveal business-sensitive bench state? Tenacious-Bench addresses this by (a) using generic company names from the Crunchbase ODM public sample, never real prospect names, and (b) representing bench capacity as relative availability (available ≥ 1, zero, or over-committed) rather than absolute headcount. The Gebru template does not surface this class of disclosure risk.

---

## References

Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H., Daumé III, H., & Crawford, K. (2021). Datasheets for Datasets. *Communications of the ACM, 64*(12), 86–92. arXiv:1803.09010.

Pushkarna, M., Zaldivar, A., & Kjartansson, O. (2022). Data Cards: Purposeful and Transparent Dataset Documentation for Responsible AI. *ACM FAccT 2022*.
