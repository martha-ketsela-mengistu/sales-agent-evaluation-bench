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
def generate_variations(seed_task: dict, num_variants: int = 4) -> List[dict]:
    """Generate variations of a seed task using Dev-tier model"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    config = get_router_config()
    model = config["families"]["qwen"]["models"][0]
    
    langfuse_context.update_current_observation(
        input={"seed_task": seed_task, "num_variants": num_variants},
        model=model
    )

    prompt = f"""Generate {num_variants} variations of this evaluation task.
Change the firmographics, numbers, and signal strength but keep the exact same failure dimension.
Do not change the core structure.
Return exactly a JSON array containing the {num_variants} variation objects.

Original task: {json.dumps(seed_task, indent=2)}"""

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
            "temperature": 0.7,
            "max_tokens": 3000,
            "response_format": {"type": "json_object"} # Some models might return an object with an array field if array is not supported at root
        }
    )
    
    res_json = response.json()
    if "error" in res_json:
        raise Exception(f"OpenRouter API error: {res_json['error']}")
        
    try:
        content = res_json["choices"][0]["message"]["content"]
        tokens_in = res_json["usage"]["prompt_tokens"]
        tokens_out = res_json["usage"]["completion_tokens"]
        
        rates = config["families"]["qwen"]["cost_per_1k_tokens"]
        cost = (tokens_in / 1000.0 * rates["input"]) + (tokens_out / 1000.0 * rates["output"])
        
        log_cost("bulk_variation", "generate_variations", model, tokens_in, tokens_out, cost)
        
        parsed = json.loads(content)
        # Handle cases where model returns {"variations": [...]} instead of [...]
        if isinstance(parsed, dict):
            for k, v in parsed.items():
                if isinstance(v, list):
                    parsed = v
                    break
                    
        if not isinstance(parsed, list):
            parsed = [parsed]
            
        langfuse_context.update_current_observation(output=parsed)
        return parsed
    except Exception as e:
        langfuse_context.update_current_observation(level="ERROR", status_message=str(e))
        raise

@observe()
def expand_seeds(seeds: List[dict], variants_per_seed: int = 4) -> List[dict]:
    all_tasks = []
    for seed in seeds:
        try:
            vars_tasks = generate_variations(seed, variants_per_seed)
            # Annotate with metadata
            for t in vars_tasks:
                if "metadata" not in t:
                    t["metadata"] = {}
                t["metadata"]["source_mode"] = "multi-llm-synthesis"
            all_tasks.extend(vars_tasks)
        except Exception as e:
            print(f"Error expanding seed: {e}")
    return all_tasks
