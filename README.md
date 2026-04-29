# Tenacious-Bench: Sales Agent Evaluation Bench

## Overview
Tenacious-Bench is a domain-specific evaluation dataset designed to measure the performance of the Tenacious Conversion Engine on B2B sales tasks. Unlike generic benchmarks, Tenacious-Bench focuses on the specific nuances of our business, including our voice, market segments, and failure modes. It uses a combination of trace-derived examples, programmatic parameter sweeps, multi-LLM synthesis, and hand-authored adversarial tasks to create a robust, contamination-resistant evaluation dataset.

## Status
- **Act I**: Completed. Audit memo and base schema design finished.
- **Act II**: In Progress. Currently implementing the Multi-LLM synthesis pipeline (Mode 3) to generate complex, adversarial edge cases and populate the 50/30/20 partitioned dataset.
- **Act III - V**: Pending.

## Setup

### Prerequisites
- Python 3.11+
- HuggingFace account and access token
- OpenRouter account and API key
- Google Colab account (for T4 GPU training) or local environment with GPU

### Installation
1. Clone the repository.
2. Install the required Python packages:
   ```bash
   pip install transformers peft trl datasets accelerate bitsandbytes
   ```
3. Set your environment variables for HuggingFace and OpenRouter tokens:
   ```bash
   export HF_TOKEN="your_huggingface_token"
   export OPENROUTER_API_KEY="your_openrouter_key"
   ```

## What is Next
1. Finalize the `run_synthesis()` pipeline for the multi-LLM dataset generation.
2. Apply the LLM-as-a-judge filter and contamination checks (n-gram, embedding, and time-shift) before sealing the held-out partition.
3. Prepare the training data partition (Path A, B, or C) and begin the training and ablation phase.
