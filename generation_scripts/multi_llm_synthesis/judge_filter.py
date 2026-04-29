import json
import os
import requests
from typing import List, Dict
from langfuse.decorators import observe, langfuse_context
import sys
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from cost_tracker import log_cost

LOG_FILE = Path(__file__).parent.parent / "judge_filter_log.jsonl"

def get_router_config() -> dict:
    path = os.path.join(os.path.dirname(__file__), "..", "router_config.json")
    with open(path, "r") as f:
        return json.load(f)

def parse_scores(text: str) -> List[int]:
    """Parse comma separated scores from text."""
    import re
    # Extract numbers 1-5 from text
    nums = [int(n) for n in re.findall(r'[1-5]', text)]
    if len(nums) >= 3:
        return nums[:3]
    return [0, 0, 0] # fallback

@observe()
def judge_filter_task(task_json: dict) -> bool:
    """Judge a task on 3 dimensions. Return True if it passes."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    config = get_router_config()
    model = config["families"]["deepseek"]["models"][0]
    
    langfuse_context.update_current_observation(
        input={"task": task_json},
        model=model
    )

    prompt = f"""Score this evaluation task 1-5 on each dimension:

1. INPUT COHERENCE: Are inputs internally consistent and realistic?
2. GROUND-TRUTH VERIFIABILITY: Is the correct answer unambiguous?
3. RUBRIC-APPLICATION CLARITY: Can the rubric be applied without ambiguity?

Return only three comma-separated numbers, e.g., 5, 4, 4.

Task: {json.dumps(task_json, indent=2)}"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://localhost:3000",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 50
        }
    )
    
    res_json = response.json()
    if "error" in res_json:
        raise Exception(f"OpenRouter API error: {res_json['error']}")
        
    try:
        content = res_json["choices"][0]["message"]["content"]
        tokens_in = res_json["usage"]["prompt_tokens"]
        tokens_out = res_json["usage"]["completion_tokens"]
        
        rates = config["families"]["deepseek"]["cost_per_1k_tokens"]
        cost = (tokens_in / 1000.0 * rates["input"]) + (tokens_out / 1000.0 * rates["output"])
        
        log_cost("judge_filter", "judge_task", model, tokens_in, tokens_out, cost)
        
        scores = parse_scores(content)
        
        # Criteria for passing:
        # Input Coherence (≥ 4)
        # Ground-truth Verifiability (≥ 4)
        # Rubric-application Clarity (≥ 3)
        passed = (scores[0] >= 4 and scores[1] >= 4 and scores[2] >= 3)
        
        # Log to file
        with open(LOG_FILE, "a") as f:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "task_id": task_json.get("task_id", "unknown"),
                "scores": scores,
                "passed": passed
            }
            f.write(json.dumps(log_entry) + "\n")
            
        langfuse_context.update_current_observation(output={"scores": scores, "passed": passed})
        return passed
    except Exception as e:
        langfuse_context.update_current_observation(level="ERROR", status_message=str(e))
        return False

@observe()
def filter_tasks(tasks: List[dict]) -> List[dict]:
    passed_tasks = []
    for t in tasks:
        if judge_filter_task(t):
            passed_tasks.append(t)
    return passed_tasks
