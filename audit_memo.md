# Audit Memo — τ²-Bench Gap Analysis for Tenacious-Bench v0.1

**Date:** 2026-04-29
**Author:** Martha Ketsela Mengistu
**Question:** What does τ²-Bench retail fail to grade about Tenacious-specific behavior, and what does Week 10 evidence prove about that gap?

---

## The Core Gap

τ²-Bench retail grades task completion: did the agent find a product, compare prices, complete a checkout flow? Every metric assumes a single correct answer and the failure mode is failure to reach it.

Tenacious's failure modes are structurally different. Across 376 traces and 30 probes, the agent completes outreach in the large majority of cases. The failures are constraint violations inside completed outputs — wrong claims, missing disclaimers, banned phrases, incorrect segment routing — that τ²-Bench has no rubric for. The benchmark would score the most damaging failures as successes.

Four gaps, each proven by Week 10 evidence.

---

## Gap 1 — Signal Grounding Fidelity Is Not Graded

τ²-Bench measures whether an email was sent, not whether the email's claims are grounded in the prospect's actual signal data. Trace `b814fe09c1bbfd8a4ec09bf33639d123` and trace `1fa7b6b7eff362232c14da5f7bf80f51` both show the agent emailing Deep Cogito Inc. with AI maturity 0/3 and hiring velocity `insufficient_signal`, yet producing confident framing ("our data shows…") with no substantive grounding. Trace `f264ab49fa6cdc6952224d63481da737` (Atommap Corp) shows the same Seg1 template applied to a prospect with zero open roles and no funding events. All three score as completions on τ²-Bench. None are acceptable under the Tenacious style guide's grounding rule.

Probes PROBE-2-3 (banned phrase "series a" when actual round was Seed, 5 months prior) and PROBE-9-2 (false-positive layoff signal at 4% reduction) confirm this in controlled conditions.

---

## Gap 2 — Bench Capacity Constraints Are Not Modeled

τ²-Bench has no concept of a service-provider's bench. PROBE-3-1 triggered the critical failure: the agent responded to a Rust engineering request without disclosing that `bench_summary.json` shows 0 available Rust engineers. A τ²-Bench grader would not penalize this — there is no bench-constraint check in its rubric. For Tenacious, this is a policy violation with contract-breach consequences estimated at $500K+ per incident.

---

## Gap 3 — ICP Signal Priority Ordering Is Not Tested

PROBE-1-4 exposes a rule-ordering bug: the agent classifies a prospect as Segment 2 (layoff+funding) when Segment 3 (leadership transition) should take priority, because the new-CTO reassessment window is the narrowest buying signal. τ²-Bench has no concept of segment classification, multi-signal priority ordering, or the business cost of routing to the wrong segment. An email was sent — τ²-Bench would mark the task complete. The $360K ACV opportunity was lost.

---

## Gap 4 — Phrase Compliance and Tone Consistency Are Not Enforced

PROBE-4-1 produced a reply containing banned phrase "cost arbitrage." PROBE-8-2 and PROBE-8-3 both failed on timezone-unaware scheduling language. PROBE-7-1 failed coordination language ("what time works for you" absent when it was required). τ²-Bench has no domain-specific phrase list, no banned-phrase enforcement, and no tone-marker rubric.

Comparing traces `9342fc781275cb91b5a1d3c301b0fd31` and `f93806a76753376d50ff02ecfb5aa2df` (CrossBoundary, correctly skipped) against traces `b814fe09` and `f264ab49` (outreach sent with no signal) reveals the inconsistency pattern: the agent correctly withholds outreach when the overall decision is `abstain`, but the same discipline does not carry into email composition when a segment override is applied. τ²-Bench cannot detect this because it evaluates tasks independently, not across difficulty variants of the same scenario.

Also cited: PROBE-10-2 (gap over-claiming), PROBE-2-3.

---

## Schema Dimensions for Tenacious-Bench v0.1

Five grading dimensions follow from this audit:

| Dimension | Graded by |
|---|---|
| Signal grounding fidelity | Required-signal reference check; hedging-language check on low-confidence scores |
| Bench capacity honesty | Disclaimer presence check against `bench_summary.json` slice |
| ICP segment accuracy | Exact-match against correct segment given input signals |
| Phrase compliance | Banned-phrase scan + required-phrase scan (deterministic string matching) |
| Tone marker preservation | LLM judge on the five Tenacious style-guide markers (0–5 scale each) |

Each dimension is machine-gradable from the task schema. No human is required in the scoring loop for Dimensions 1–4. Dimension 5 uses an LLM judge with a fixed rubric prompt.
