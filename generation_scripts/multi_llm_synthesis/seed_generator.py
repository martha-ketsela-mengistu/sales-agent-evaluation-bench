import json
import os
import requests
from typing import List, Dict
from langfuse.decorators import observe, langfuse_context
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from cost_tracker import log_cost

def get_router_config() -> dict:
    path = os.path.join(os.path.dirname(__file__), "..", "router_config.json")
    with open(path, "r") as f:
        return json.load(f)

@observe()
def generate_seed_task(taxonomy: str, rubric: str) -> dict:
    """Generate a single seed task from a Frontier model"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    config = get_router_config()
    model = config["families"]["anthropic"]["models"][0]
    
    # Langfuse context
    langfuse_context.update_current_observation(
        input={"taxonomy": taxonomy, "rubric": rubric},
        model=model
    )

    prompt = f"""Generate a hard evaluation case for a B2B sales agent.

Failure taxonomy: {taxonomy}

Rubric dimensions: {rubric}

Generate ONE task as JSON with: input_context (containing prospect_brief, bench_summary, prior_thread), candidate_output, ground_truth, and evaluator_config.
The candidate output should look correct but violate one dimension.
Make it realistic — use Crunchbase-style firmographics.
Ensure the response is valid JSON only."""

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
            "temperature": 0.8,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
    )
    
    res_json = response.json()
    if "error" in res_json:
        raise Exception(f"OpenRouter API error: {res_json['error']}")
        
    try:
        content = res_json["choices"][0]["message"]["content"]
        tokens_in = res_json["usage"]["prompt_tokens"]
        tokens_out = res_json["usage"]["completion_tokens"]
        
        rates = config["families"]["anthropic"]["cost_per_1k_tokens"]
        cost = (tokens_in / 1000.0 * rates["input"]) + (tokens_out / 1000.0 * rates["output"])
        
        log_cost("seed_generation", "generate_seed", model, tokens_in, tokens_out, cost)
        
        task_data = json.loads(content)
        langfuse_context.update_current_observation(output=task_data)
        return task_data
    except Exception as e:
        langfuse_context.update_current_observation(level="ERROR", status_message=str(e))
        raise

@observe()
def generate_seed_tasks(num_tasks: int, taxonomy: str, rubric: str) -> List[dict]:
    tasks = []
    # Cap at 50 per budget
    num_tasks = min(num_tasks, 50)
    for i in range(num_tasks):
        try:
            task = generate_seed_task(taxonomy, rubric)
            tasks.append(task)
        except Exception as e:
            print(f"Error generating seed task {i}: {e}")
    return tasks
