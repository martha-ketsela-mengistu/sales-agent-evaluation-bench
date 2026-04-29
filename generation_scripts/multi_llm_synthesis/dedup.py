import sys
import os
from typing import List

def get_task_text(task: dict) -> str:
    """Extract semantic text from task for embedding"""
    ctx = task.get("input_context", {})
    brief = ctx.get("prospect_brief", {})
    parts = [
        brief.get("company_name", ""),
        str(brief.get("funding", {}).get("stage", "")),
        str(brief.get("hiring_signal_brief", {}).get("open_roles", "")),
        task.get("metadata", {}).get("category", "")
    ]
    return " ".join(parts)

def embedding_deduplicate(new_tasks: List[dict], existing_tasks: List[dict], threshold=0.85) -> List[dict]:
    """Filter out new_tasks that are semantically too similar to existing_tasks"""
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        print("sentence-transformers not installed. Skipping embedding dedup.")
        return new_tasks
        
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    if not existing_tasks:
        return new_tasks
        
    existing_texts = [get_task_text(t) for t in existing_tasks]
    existing_embeddings = model.encode(existing_texts, convert_to_tensor=True)
    
    unique_tasks = []
    removed = 0
    for t in new_tasks:
        text = get_task_text(t)
        emb = model.encode(text, convert_to_tensor=True)
        cos_scores = util.cos_sim(emb, existing_embeddings)[0]
        if max(cos_scores) < threshold:
            unique_tasks.append(t)
            # Add this to existing to avoid duplicates within the new tasks
            existing_texts.append(text)
            # this is slow but fine for small n
            existing_embeddings = model.encode(existing_texts, convert_to_tensor=True)
        else:
            removed += 1
            
    print(f"  [dedup] removed {removed} tasks via embedding deduplication")
    return unique_tasks
