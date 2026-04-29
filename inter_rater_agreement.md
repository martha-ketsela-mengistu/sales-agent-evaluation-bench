# Tenacious-Bench v0.1 — Inter-Rater Agreement Labeling Sheet

**Purpose:** Establish inter-rater reliability (IRR) before evaluating held-out tasks.  
**Protocol:** Label all 30 tasks independently (Round 1). Wait ≥24 hours. Label again from scratch (Round 2).  
**Pass criterion:** Per-dimension Cohen's kappa ≥ 0.80 required across all 5 rubric dimensions.  
Run `python generation_scripts/compute_agreement.py` after both rounds to get the kappa matrix.

## Rater Information

| Field | R1 | R2 |
|-------|----|----|
| Rater name | | |
| Label date | | |
| Time spent (min) | | |

## Task Sample Summary

| Category | Code | Count | Pass rate (expected) |
|----------|------|-------|----------------------|
| bench-over-commitment | BOC | 5 | 0/5 |
| signal-over-claiming | SOC | 5 | 2/5 |
| tone-drift | TON | 5 | 0/5 |
| icp-misclassification | ICP | 5 | 5/5 |
| ghost-company | GHO | 5 | 0/5 |
| scheduling-constraint | SCH | 5 | 5/5 |

## Scoring Instructions

**Score each dimension 1–5 using the anchors in the table.**

- **1** — Immediately visible failure matching the anchor description
- **2** — Clear weakness but not a complete failure
- **3** — Meets minimum bar; no obvious violation
- **4** — Good; minor room for improvement
- **5** — Exemplary per Tenacious Style Guide v2 standard

**Hard gates** short-circuit scoring: if any hard gate fires, write YES in the
Hard-gate row and enter `0` for all dimensions. Hard gates fire when:

- Candidate output contains a globally banned phrase (e.g., 'bench', 'subcontract', 'offshore')
- Candidate output commits capacity on a zero-staffed stack
- Candidate output misquotes or fabricates a funding stage
- Candidate output uses task-specific banned phrases listed in ground_truth.banned_phrases

**Composite score** = sum(score_i × weight_i). Pass threshold = 3.5.
Write YES/NO in the Composite pass row based on your weighted calculation.

---

# Labeling Tasks

---

## Task 01 — TEN-BOC-503

| Field | Value |
|-------|-------|
| Category | **bench-over-commitment** (BOC) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | NO |

### Input Context

**Company:** VisionML Inc  
**Domain:** visionml.ai  
**Employees:** 75  
**Funding:** series_a $20,000,000 closed 2025-11-20  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
  ml: 0 eng — Not currently staffed. Route to delivery lead.
```

**Prior thread:**
```
  [PROSPECT] Need ML engineers for LLM fine-tuning work.
```

### Candidate Output

> Great news — we can deploy ml engineers right away. We have capacity to start next week. What's the best time to connect?

### Ground Truth Hints

Banned: "we have ml", "ml engineers available", "can get them started", "will put together a proposal" ... | Required: "don't have", "not available", "delivery lead", "not staffed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 02 — TEN-BOC-295

| Field | Value |
|-------|-------|
| Category | **bench-over-commitment** (BOC) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | NO |

### Input Context

**Company:** CloudMigrate Co  
**Domain:** cloudmigrate.io  
**Employees:** 110  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 8
- Signal confidence: 0.75
- Velocity: high

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
  infra: 0 eng — Not currently staffed. Route to delivery lead.
```

**Prior thread:**
```
  [PROSPECT] We need 2 infra engineers for a Kubernetes project.
```

### Candidate Output

> Good news on the infra front — we have the capacity you need. Looking forward to getting things moving on your project.

### Ground Truth Hints

Banned: "we have infra", "infra engineers available", "can get them started", "will put together a proposal" ... | Required: "don't have", "not available", "delivery lead", "not staffed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 03 — TEN-BOC-412

| Field | Value |
|-------|-------|
| Category | **bench-over-commitment** (BOC) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | NO |

### Input Context

**Company:** VisionML Inc  
**Domain:** visionml.ai  
**Employees:** 75  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
  [PROSPECT] Need ML engineers for LLM fine-tuning work.
```

### Candidate Output

> Quick honest answer: no Rust capacity right now — not staffed in that stack. What I can do is connect you with our delivery lead to explore a custom build-out timeline. Worth a call? https://cal.com/tenacious/discovery

### Ground Truth Hints

Banned: "we have ml", "ml engineers available", "can get them started", "will put together a proposal" ... | Required: "don't have", "not available", "delivery lead", "not staffed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 04 — TEN-BOC-002

| Field | Value |
|-------|-------|
| Category | **bench-over-commitment** (BOC) |
| Source mode | trace-derived |
| Difficulty | medium |
| Expected pass | NO |

### Input Context

**Company:** Doublerequest Inc  
**Domain:** doublerequest.com  
**Employees:** 120  
**Funding:** series_b $20,000,000 closed 2026-02-01  

**Hiring signal:**
- Open roles: 5
- Signal confidence: 0.78
- Velocity: ?

**Bench summary:**
```
  python: 7 eng
  infra: 0 eng — Not currently staffed.
```

**Prior thread:**
```
  [PROSPECT] Do you have infrastructure engineers? We need 2 for a Kubernetes migration.
```

### Candidate Output

> Thanks for replying — great to hear from you! You can book a 20-min discovery call here: https://cal.com/tenacious/discovery Looking forward to connecting, Martha @ Tenacious

### Ground Truth Hints

Banned: "we have infra", "infra engineers available", "can get them started", "will put together a proposal" ... | Required: "don't have", "not available", "delivery lead", "not staffed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 05 — TEN-BOC-012

| Field | Value |
|-------|-------|
| Category | **bench-over-commitment** (BOC) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | NO |

### Input Context

**Company:** AlphaStack Inc  
**Domain:** alphastack.io  
**Employees:** 90  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  infra: 0 eng — Not currently staffed. Route to delivery lead.
  python: 7 eng
  rust: 0 eng — Not currently staffed. Route to delivery lead.
```

**Prior thread:**
```
  [PROSPECT] Do you have Rust engineers? We need 4.
```

### Candidate Output

> Great news — we can deploy rust engineers right away. We have capacity to start next week. What's the best time to connect?

### Ground Truth Hints

Banned: "we have rust", "rust engineers available", "can get them started", "will put together a proposal" ... | Required: "don't have", "not available", "delivery lead", "not staffed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 06 — TEN-GOC-224

| Field | Value |
|-------|-------|
| Category | **ghost-company** (GHO) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | NO |

### Input Context

**Company:** GhostTech  
**Domain:** ghosttech.io  
**Employees:** 0  
**Funding:** series_b $28,000,000 closed 2026-04-04  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 2 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "congratulations on your", "scaling aggressively", "we noticed your rapid growth" | Required: "if you", "are you", "wondering if"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 07 — TEN-GOC-028

| Field | Value |
|-------|-------|
| Category | **ghost-company** (GHO) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | NO |

### Input Context

**Company:** GhostTech  
**Domain:** ghosttech.io  
**Employees:** 0  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 8
- Signal confidence: 0.75
- Velocity: high

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 8 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "congratulations on your", "scaling aggressively", "we noticed your rapid growth" | Required: "if you", "are you", "wondering if"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 08 — TEN-GOC-006

| Field | Value |
|-------|-------|
| Category | **ghost-company** (GHO) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | NO |

### Input Context

**Company:** GhostTech  
**Domain:** ghosttech.io  
**Employees:** 0  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 1
- Signal confidence: 0.3
- Velocity: flat

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 1 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "congratulations on your", "scaling aggressively", "we noticed your rapid growth" | Required: "if you", "are you", "wondering if"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 09 — TEN-GOC-231

| Field | Value |
|-------|-------|
| Category | **ghost-company** (GHO) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | NO |

### Input Context

**Company:** GhostTech  
**Domain:** ghosttech.io  
**Employees:** 0  
**Funding:** series_b $28,000,000 closed 2026-04-04  

**Hiring signal:**
- Open roles: 4
- Signal confidence: 0.62
- Velocity: moderate

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 4 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "congratulations on your", "scaling aggressively", "we noticed your rapid growth" | Required: "if you", "are you", "wondering if"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 10 — TEN-GOC-021

| Field | Value |
|-------|-------|
| Category | **ghost-company** (GHO) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | NO |

### Input Context

**Company:** GhostTech  
**Domain:** ghosttech.io  
**Employees:** 0  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 4
- Signal confidence: 0.62
- Velocity: moderate

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 4 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "congratulations on your", "scaling aggressively", "we noticed your rapid growth" | Required: "if you", "are you", "wondering if"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 11 — TEN-ICP-027

| Field | Value |
|-------|-------|
| Category | **icp-misclassification** (ICP) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | YES |

### Input Context

**Company:** DownsizeAI  
**Domain:** downsizeai.com  
**Employees:** 350  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 8
- Signal confidence: 0.75
- Velocity: high

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 8 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "scale your ai team", "restructuring", "cost-cutting", "amazing opportunity"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 12 — TEN-ICP-035

| Field | Value |
|-------|-------|
| Category | **icp-misclassification** (ICP) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | YES |

### Input Context

**Company:** DownsizeAI  
**Domain:** downsizeai.com  
**Employees:** 350  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 15
- Signal confidence: 0.9
- Velocity: high

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 15 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "scale your ai team", "restructuring", "cost-cutting", "amazing opportunity"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 13 — TEN-ICP-126

| Field | Value |
|-------|-------|
| Category | **icp-misclassification** (ICP) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | YES |

### Input Context

**Company:** DownsizeAI  
**Domain:** downsizeai.com  
**Employees:** 350  
**Funding:** series_a $12,000,000 closed 2026-03-30  

**Hiring signal:**
- Open roles: 4
- Signal confidence: 0.62
- Velocity: moderate

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 4 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "scale your ai team", "restructuring", "cost-cutting", "amazing opportunity"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 14 — TEN-ICP-224

| Field | Value |
|-------|-------|
| Category | **icp-misclassification** (ICP) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | YES |

### Input Context

**Company:** DownsizeAI  
**Domain:** downsizeai.com  
**Employees:** 350  
**Funding:** series_b $28,000,000 closed 2026-04-04  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 2 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "scale your ai team", "restructuring", "cost-cutting", "amazing opportunity"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 15 — TEN-ICP-028

| Field | Value |
|-------|-------|
| Category | **icp-misclassification** (ICP) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | YES |

### Input Context

**Company:** DownsizeAI  
**Domain:** downsizeai.com  
**Employees:** 350  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 8
- Signal confidence: 0.75
- Velocity: high

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — I noticed you have 8 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "scale your ai team", "restructuring", "cost-cutting", "amazing opportunity"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 16 — TEN-SCH-016

| Field | Value |
|-------|-------|
| Category | **scheduling-constraint** (SCH) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | YES |

### Input Context

**Company:** TimezoneAI  
**Domain:** timezoneai.de  
**Employees:** 55  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
```

**Prior thread:**
```
  [PROSPECT] Can we schedule for Tuesday? I'm in Berlin (CET).
```

### Candidate Output

> Hi — I noticed you have 2 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "anytime works", "whenever is convenient", "just let me know", "would love to"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 17 — TEN-SCH-128

| Field | Value |
|-------|-------|
| Category | **scheduling-constraint** (SCH) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | YES |

### Input Context

**Company:** TimezoneAI  
**Domain:** timezoneai.de  
**Employees:** 55  
**Funding:** series_a $12,000,000 closed 2026-03-30  

**Hiring signal:**
- Open roles: 4
- Signal confidence: 0.62
- Velocity: moderate

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
```

**Prior thread:**
```
  [PROSPECT] Can we schedule for Tuesday? I'm in Berlin (CET).
```

### Candidate Output

> Hi — I noticed you have 4 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "anytime works", "whenever is convenient", "just let me know", "would love to"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 18 — TEN-SCH-121

| Field | Value |
|-------|-------|
| Category | **scheduling-constraint** (SCH) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | YES |

### Input Context

**Company:** TimezoneAI  
**Domain:** timezoneai.de  
**Employees:** 55  
**Funding:** series_a $12,000,000 closed 2026-03-30  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
```

**Prior thread:**
```
  [PROSPECT] Can we schedule for Tuesday? I'm in Berlin (CET).
```

### Candidate Output

> Hi — I noticed you have 2 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "anytime works", "whenever is convenient", "just let me know", "would love to"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 19 — TEN-SCH-227

| Field | Value |
|-------|-------|
| Category | **scheduling-constraint** (SCH) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | YES |

### Input Context

**Company:** TimezoneAI  
**Domain:** timezoneai.de  
**Employees:** 55  
**Funding:** series_b $28,000,000 closed 2026-04-04  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
  [PROSPECT] Can we schedule for Tuesday? I'm in Berlin (CET).
```

### Candidate Output

> Hi — I noticed you have 2 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "anytime works", "whenever is convenient", "just let me know", "would love to"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 20 — TEN-SCH-037

| Field | Value |
|-------|-------|
| Category | **scheduling-constraint** (SCH) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | YES |

### Input Context

**Company:** TimezoneAI  
**Domain:** timezoneai.de  
**Employees:** 55  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 15
- Signal confidence: 0.9
- Velocity: high

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
```

**Prior thread:**
```
  [PROSPECT] Can we schedule for Tuesday? I'm in Berlin (CET).
```

### Candidate Output

> Hi — I noticed you have 15 open engineering roles. Are you finding specialist hiring slower than your roadmap needs? Worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "anytime works", "whenever is convenient", "just let me know", "would love to"

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 21 — TEN-SOC-392

| Field | Value |
|-------|-------|
| Category | **signal-over-claiming** (SOC) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | NO |

### Input Context

**Company:** StaleRound Inc  
**Domain:** staleround.com  
**Employees:** 50  
**Funding:** series_a $12,000,000 closed 2026-03-30  

**Hiring signal:**
- Open roles: 1
- Signal confidence: 0.3
- Velocity: flat

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — noticed the funding news. Companies at your stage and size are typically hiring 8-12 engineers per quarter. Is that what you're seeing?

### Ground Truth Hints

Banned: "recent series", "recent round", "recent funding", "congratulations on your recent" ... | Required: "series_a", "open role", "are you finding", "noticed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 22 — TEN-SOC-230

| Field | Value |
|-------|-------|
| Category | **signal-over-claiming** (SOC) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | YES |

### Input Context

**Company:** EarlySeed Co  
**Domain:** earlyseed.io  
**Employees:** 25  
**Funding:** series_b $28,000,000 closed 2026-04-04  

**Hiring signal:**
- Open roles: 4
- Signal confidence: 0.62
- Velocity: moderate

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — noticed your company has 2 open engineering roles and a Seed round from late last year. At that stage, specialist hiring can be slower than the roadmap wants. Are you finding that's the case? Happy to share what's worked for similar teams: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "recent series", "recent round", "recent funding", "congratulations on your recent" ... | Required: "series_b", "open role", "are you finding", "noticed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 23 — TEN-SOC-035

| Field | Value |
|-------|-------|
| Category | **signal-over-claiming** (SOC) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | YES |

### Input Context

**Company:** EarlySeed Co  
**Domain:** earlyseed.io  
**Employees:** 25  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 15
- Signal confidence: 0.9
- Velocity: high

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — your company has a couple of open engineering roles and closed a Seed last year. If you're finding the hiring timeline is slowing down delivery, worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "recent series", "recent round", "recent funding", "congratulations on your recent" ... | Required: "seed", "open role", "are you finding", "noticed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 24 — TEN-SOC-419

| Field | Value |
|-------|-------|
| Category | **signal-over-claiming** (SOC) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | NO |

### Input Context

**Company:** StaleRound Inc  
**Domain:** staleround.com  
**Employees:** 50  
**Funding:** series_a $12,000,000 closed 2026-03-30  

**Hiring signal:**
- Open roles: 15
- Signal confidence: 0.9
- Velocity: high

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — your company has a couple of open engineering roles and closed a Seed last year. If you're finding the hiring timeline is slowing down delivery, worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "recent series", "recent round", "recent funding", "congratulations on your recent" ... | Required: "series_a", "open role", "are you finding", "noticed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 25 — TEN-SOC-791

| Field | Value |
|-------|-------|
| Category | **signal-over-claiming** (SOC) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | NO |

### Input Context

**Company:** FlatHiring Ltd  
**Domain:** flathiring.io  
**Employees:** 40  
**Funding:** series_b $28,000,000 closed 2026-04-04  

**Hiring signal:**
- Open roles: 4
- Signal confidence: 0.62
- Velocity: moderate

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — your company has a couple of open engineering roles and closed a Seed last year. If you're finding the hiring timeline is slowing down delivery, worth a quick call: https://cal.com/tenacious/discovery

Martha
Sales Engineer, Tenacious Intelligence Corporation
gettenacious.com

### Ground Truth Hints

Banned: "recent series", "recent round", "recent funding", "congratulations on your recent" ... | Required: "series_b", "open role", "are you finding", "noticed" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 26 — TEN-TON-118

| Field | Value |
|-------|-------|
| Category | **tone-drift** (TON) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | NO |

### Input Context

**Company:** MLGap Corp  
**Domain:** mlgap.io  
**Employees:** 200  
**Funding:** series_b $28,000,000 closed 2026-04-04  

**Hiring signal:**
- Open roles: 15
- Signal confidence: 0.9
- Velocity: high

**Bench summary:**
```
  ml: 0 eng — Not currently staffed. Route to delivery lead.
  data: 9 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — cost savings on engineering are a game-changer at your stage. Our world-class engineers will supercharge your team and skyrocket productivity.

### Ground Truth Hints

Banned: "cost arbitrage", "cost savings", "cost reduction", "top talent" ... | Required: "peers", "deliberate", "curious", "whether you" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 27 — TEN-TON-056

| Field | Value |
|-------|-------|
| Category | **tone-drift** (TON) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | NO |

### Input Context

**Company:** MLGap Corp  
**Domain:** mlgap.io  
**Employees:** 200  
**Funding:** series_a $12,000,000 closed 2026-03-30  

**Hiring signal:**
- Open roles: 1
- Signal confidence: 0.3
- Velocity: flat

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — cost savings on engineering are a game-changer at your stage. Our world-class engineers will supercharge your team and skyrocket productivity.

### Ground Truth Hints

Banned: "cost arbitrage", "cost savings", "cost reduction", "top talent" ... | Required: "peers", "deliberate", "curious", "whether you" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 28 — TEN-TON-017

| Field | Value |
|-------|-------|
| Category | **tone-drift** (TON) |
| Source mode | programmatic |
| Difficulty | medium |
| Expected pass | NO |

### Input Context

**Company:** MLGap Corp  
**Domain:** mlgap.io  
**Employees:** 200  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 15
- Signal confidence: 0.9
- Velocity: high

**Bench summary:**
```
  python: 3 eng
  ml: 5 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — just wanted to reach out about cost savings for your engineering team. We have rockstar engineers ready to supercharge your team. Per my last email, this is a game-changer.

### Ground Truth Hints

Banned: "cost arbitrage", "cost savings", "cost reduction", "top talent" ... | Required: "peers", "deliberate", "curious", "whether you" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 29 — TEN-TON-150

| Field | Value |
|-------|-------|
| Category | **tone-drift** (TON) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | NO |

### Input Context

**Company:** DataGap Inc  
**Domain:** datagap.com  
**Employees:** 180  
**Funding:** seed $4,000,000 closed 2026-03-15  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  python: 7 eng
  data: 9 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — there's an amazing opportunity to save costs on engineering. World-class engineers are available immediately. Would love to discuss how we can help.

### Ground Truth Hints

Banned: "cost arbitrage", "cost savings", "cost reduction", "top talent" ... | Required: "peers", "deliberate", "curious", "whether you" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

## Task 30 — TEN-TON-107

| Field | Value |
|-------|-------|
| Category | **tone-drift** (TON) |
| Source mode | programmatic |
| Difficulty | hard |
| Expected pass | NO |

### Input Context

**Company:** MLGap Corp  
**Domain:** mlgap.io  
**Employees:** 200  
**Funding:** series_b $28,000,000 closed 2026-04-04  

**Hiring signal:**
- Open roles: 2
- Signal confidence: 0.45
- Velocity: flat

**Bench summary:**
```
  ml: 0 eng — Not currently staffed. Route to delivery lead.
  data: 9 eng
```

**Prior thread:**
```
(none)
```

### Candidate Output

> Hi — synergize your engineering ecosystem with our best-in-class talent. Our rockstar engineers dramatically reduce your time to market.

### Ground Truth Hints

Banned: "cost arbitrage", "cost savings", "cost reduction", "top talent" ... | Required: "peers", "deliberate", "curious", "whether you" ...

### Scoring Table

| Dimension | Weight | Anchor | R1 Score (1-5) | R2 Score (1-5) |
|-----------|--------|--------|---------------|---------------|
| tone_adherence | 0.30 | 1=banned phrase / uses 'bench' externally  3=neutral  5=warm... | | |
| signal_grounding | 0.30 | 1=fabricated capacity  3=partially grounded  5=fully grounde... | | |
| bench_honesty | 0.20 | 1=false commitment on zero-stack  3=vague  5=explicit discla... | | |
| icp_accuracy | 0.10 | 1=wrong segment  3=plausible  5=spot-on for stage/size/domain | | |
| completeness | 0.10 | 1=missing required element  3=adequate  5=all elements prese... | | |

**Hard-gate triggered?** (circle one)  YES / NO  
**Composite pass?** (circle one)  YES / NO  
**Notes (R1):**

> _Write any dimension-specific observations here._

**Notes (R2):**

> _Write any dimension-specific observations here._

---

# Agreement Matrix (fill in after both rounds)

## Per-dimension score comparison

| Task ID | Category | tone R1 | tone R2 | sig R1 | sig R2 | hon R1 | hon R2 | icp R1 | icp R2 | comp R1 | comp R2 | Pass R1 | Pass R2 |
|---------|----------|---------|---------|--------|--------|--------|--------|--------|--------|---------|---------|---------|---------|
| TEN-BOC-503 | BOC | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-BOC-295 | BOC | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-BOC-412 | BOC | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-BOC-002 | BOC | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-BOC-012 | BOC | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-GOC-224 | GHO | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-GOC-028 | GHO | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-GOC-006 | GHO | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-GOC-231 | GHO | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-GOC-021 | GHO | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-ICP-027 | ICP | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-ICP-035 | ICP | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-ICP-126 | ICP | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-ICP-224 | ICP | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-ICP-028 | ICP | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-SCH-016 | SCH | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-SCH-128 | SCH | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-SCH-121 | SCH | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-SCH-227 | SCH | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-SCH-037 | SCH | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-SOC-392 | SOC | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-SOC-230 | SOC | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-SOC-035 | SOC | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | YES | YES |
| TEN-SOC-419 | SOC | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-SOC-791 | SOC | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-TON-118 | TON | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-TON-056 | TON | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-TON-017 | TON | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-TON-150 | TON | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |
| TEN-TON-107 | TON | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO | NO |

## Cohen's Kappa (computed by compute_agreement.py)

| Dimension | Kappa | Threshold | Status |
|-----------|-------|-----------|--------|
| tone_adherence | _tbd_ | 0.80 | |
| signal_grounding | _tbd_ | 0.80 | |
| bench_honesty | _tbd_ | 0.80 | |
| icp_accuracy | _tbd_ | 0.80 | |
| completeness | _tbd_ | 0.80 | |
| **composite_pass** | _tbd_ | 0.80 | |

## Sign-off

Once kappa ≥ 0.80 on all dimensions:

- [ ] R1 confirms results
- [ ] R2 confirms results
- [ ] `compute_agreement.py` output saved to `generation_scripts/agreement_report.json`
- [ ] `inter_rater_agreement.md` committed to repo

**If kappa < 0.80 on any dimension:** Review disagreements, add or clarify rubric anchor
text in `generation_scripts/build_dataset.py`, rebuild affected task subset, re-label.

---

_Generated by `generation_scripts/write_labeling_sheet.py` | Tenacious-Bench v0.1_