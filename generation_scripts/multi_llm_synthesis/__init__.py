import json
import os
from pathlib import Path
from typing import List

from .seed_generator import generate_seed_tasks
from .bulk_variation import expand_seeds
from .judge_filter import filter_tasks
from .dedup import embedding_deduplicate

def run_synthesis(existing_tasks: List[dict]) -> List[dict]:
    """
    Run the synthesis pipeline to generate new tasks.
    Target ~25% of total dataset (about 80-100 tasks).
    """
    print("    [Synthesis] 1. Generating seed tasks via Frontier model...")
    # Use failure taxonomy categories
    categories = [
        "bench-over-commitment",
        "signal-over-claiming",
        "tone-drift",
        "icp-misclassification",
        "multi-thread-conflict",
        "ghost-company"
    ]
    
    seeds = []
    # generate 1 seed per category to save cost
    for cat in categories:
        taxonomy = f"Failure category: {cat}"
        rubric = "Standard 5-dimension rubric (Tone, Grounding, Honesty, ICP, Completeness)"
        try:
            # Generate 2 seed tasks per category for more diversity
            cat_seeds = generate_seed_tasks(num_tasks=2, taxonomy=taxonomy, rubric=rubric)
            seeds.extend(cat_seeds)
        except Exception as e:
            print(f"      [Synthesis] Error on seed {cat}: {e}")
            
    print(f"    [Synthesis] Generated {len(seeds)} seed tasks.")
    
    if not seeds:
        print("    [Synthesis] No seeds generated. Aborting synthesis.")
        return []

    print("    [Synthesis] 2. Generating bulk variations via Dev model...")
    variants = expand_seeds(seeds, variants_per_seed=15) # target 90 variations
    print(f"    [Synthesis] Generated {len(variants)} variants.")

    print("    [Synthesis] 3. Filtering variants via Judge model...")
    passed_variants = filter_tasks(variants)
    print(f"    [Synthesis] {len(passed_variants)} variants passed judge filter.")

    print("    [Synthesis] 4. Deduplicating against existing tasks...")
    unique_tasks = embedding_deduplicate(passed_variants, existing_tasks)
    
    print(f"    [Synthesis] Complete. Returning {len(unique_tasks)} synthesis tasks.")
    return unique_tasks
