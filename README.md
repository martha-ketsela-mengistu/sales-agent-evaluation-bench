# Tenacious-Bench: Sales Agent Evaluation Bench

## Overview

Tenacious-Bench v0.1 is a 283-task domain-specific evaluation benchmark for B2B sales outreach agents.
It measures constraint-violation failure modes — bench over-commitment, signal over-claiming, ICP misclassification,
tone drift, ghost-company outreach, and multi-thread conflict — that public benchmarks (including τ²-Bench retail)
do not grade. Scoring is fully automated via a Python evaluator combining deterministic hard gates and an
LLM judge (Claude Sonnet 4.6 via OpenRouter).

**Training path:** B — preference-tuned ORPO judge on Qwen 3.5 0.8B.

## Public Artifacts

| Artifact | URL |
|----------|-----|
| HuggingFace dataset | https://huggingface.co/datasets/marthaket/tenacious-bench-v01 |
| HuggingFace model (ORPO adapter) | https://huggingface.co/marthaket/tenacious-judge-orpo-qwen |
| Blog post | https://medium.com/@marthaket30/building-tenacious-bench-v0-1-b78a0009a54a |

## Quickstart — Reproduce the Baseline Score

Requires Python 3.12+, OPENROUTER_API_KEY (or ANTHROPIC_API_KEY), no GPU.

```bash
git clone <repo-url>
cd sales-agent-evaluation-bench
pip install -r requirements.txt
cp .env.example .env        # add OPENROUTER_API_KEY
```

Run the deterministic evaluator on the held-out partition:

```bash
python scoring_evaluator.py \
  --partition tenacious_bench_v0.1/held_out.jsonl \
  --no-llm
```

Run both baselines (deterministic + Claude LLM judge):

```bash
python ablations/run_ablations.py --no-orpo \
  --output ablations/ablation_results.json
```

Expected output:

```
Method          n   correct   det_rate
deterministic  33        33     1.0000
claude         33        33     1.0000
```

To run Delta A/B (ORPO adapter vs baselines), a T4 GPU is required:

```bash
# On Colab or RunPod with CUDA
python ablations/run_ablations.py \
  --hf-repo marthaket/tenacious-judge-orpo-qwen \
  --output ablations/ablation_results.json
```

## Repository Layout

```
audit_memo.md               Gap analysis (τ²-Bench vs Tenacious-specific requirements)
schema.json                 Tenacious-Bench v0.1 task schema with 3 example tasks
scoring_evaluator.py        Automated scorer (deterministic hard gates + LLM judge)
methodology.md              Path B declaration and justification
methodology_rationale.md    Training algorithm selection, hyperparameters, expected outcomes
datasheet.md                Gebru + Pushkarna dataset documentation (CC-BY-4.0)
inter_rater_agreement.md    30-task double-labeling sheet and kappa matrix

tenacious_bench_v0.1/
  train.jsonl               139 tasks (49%)
  dev.jsonl                 85 tasks (30%)
  held_out.jsonl            59 tasks (21%)

generation_scripts/
  build_dataset.py          Four-mode dataset authoring pipeline
  build_training_data.py    ORPO pair construction
  contamination_check.py    N-gram, embedding, and time-shift checks
  multi_llm_synthesis/      Seed generation, bulk variation, judge filter, dedup

training/
  train_orpo.ipynb          ORPO fine-tune notebook (Unsloth, Qwen 3.5 0.8B, Colab T4)
  hyperparams.json          Pinned hyperparameters (lr=2e-4, rank=8, seed=42)
  training_run.log          Step/loss log (84 steps, final loss 0.361)

training_data/
  orpo_pairs.jsonl          110 (chosen, rejected) pairs for ORPO training

ablations/
  run_ablations.py          Ablation harness (det / claude / untrained_qwen / orpo)
  ablation_results.json     Current results (det + claude baselines; ORPO pending GPU)

synthesis_memos/            8 paper synthesis memos (4 common + 4 Path B)
model_card.md               ORPO adapter card (backbone, training data, intended use)
cost_log.json               Full API and compute cost log ($1.9992 total)
```

## Setup

### Prerequisites

- Python 3.12+
- OpenRouter API key (or Anthropic API key)
- HuggingFace account and write token (for publishing)
- Google Colab T4 or CUDA GPU (for ORPO inference / Delta A/B)

### Installation

```bash
pip install -r requirements.txt
```

Or with uv:

```bash
uv sync
```

Set environment variables:

```bash
export OPENROUTER_API_KEY="your_openrouter_key"
export HF_TOKEN="your_huggingface_token"        # for publishing only
```

## Dataset

283 tasks across 6 failure-mode dimensions, 4 authoring modes, 3 partitions.

| Partition | Tasks | Share |
|-----------|-------|-------|
| train     | 139   | 49%   |
| dev       | 85    | 30%   |
| held_out  | 59    | 21%   |

| Authoring mode       | Tasks | Share |
|----------------------|-------|-------|
| trace-derived        | 75    | 26%   |
| programmatic         | 75    | 26%   |
| multi-llm-synthesis  | 128   | 45%   |
| hand-authored        | 5     | 2%    |

Dataset license: CC-BY-4.0. See [datasheet.md](datasheet.md).

## Training

Path B — ORPO preference-tuned judge. Backbone: `Qwen/Qwen3.5-0.8B`. LoRA rank 8, alpha 16.
Trained on 110 (chosen, rejected) pairs on Colab T4 (659 s, 3 epochs / 84 steps, final loss 0.361).
Adapter published at [marthaket/tenacious-judge-orpo-qwen](https://huggingface.co/marthaket/tenacious-judge-orpo-qwen).

See [methodology_rationale.md](methodology_rationale.md) and [model_card.md](model_card.md).

## Ablation Results

| Method | n | detection_rate | Delta vs Claude |
|--------|---|---------------|-----------------|
| deterministic | 33 | 1.0000 | — |
| claude (Week 10 baseline) | 33 | 1.0000 | — |
| untrained_qwen | — | pending GPU | — |
| orpo (trained adapter) | — | pending GPU | Delta A TBD |

Delta A target: ≥ +0.03 (3 pp) with p < 0.05 (paired bootstrap, 2000 resamples, seed 42).
Delta B (ORPO vs untrained Qwen): TBD.

## Cost Log

Total API and compute spend: **$3.12**. Full log in [cost_log.json](cost_log.json).

## License

Code: MIT. Dataset (tenacious_bench_v0.1/): CC-BY-4.0.

## Attribution

Martha Ketsela Mengistu — TRP1 Week 11.

