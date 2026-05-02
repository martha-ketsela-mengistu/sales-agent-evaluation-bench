import json
import os
import re
import requests
from typing import List, Dict
from langfuse import get_client, observe
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from cost_tracker import log_cost


def _repair_json(text: str) -> str:
    """Fix common LLM JSON issues: unescaped newlines/tabs inside strings."""
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == "\\" and in_string:
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch == "\n":
            result.append("\\n")
            continue
        if in_string and ch == "\r":
            result.append("\\r")
            continue
        if in_string and ch == "\t":
            result.append("\\t")
            continue
        result.append(ch)
    return "".join(result)


def _extract_partial_array(text: str) -> list:
    """
    Parse as many complete JSON objects as possible from a (possibly
    truncated or malformed) JSON array string.
    """
    text = text.strip()
    # Strip markdown fencing
    fenced = re.search(r"```(?:json)?\s*([\[\{].*)", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
        text = re.sub(r"```\s*$", "", text, flags=re.DOTALL).strip()

    # Find start of array or first {
    arr_start = text.find("[")
    obj_start = text.find("{")
    if arr_start == -1 and obj_start == -1:
        return []
    if arr_start == -1 or (obj_start != -1 and obj_start < arr_start):
        text = "[" + text[obj_start:]
    else:
        text = text[arr_start:]

    # Try direct parse
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        pass

    # Try after repairing control characters
    try:
        parsed = json.loads(_repair_json(text))
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        pass

    # Partial recovery: extract each complete top-level { ... } object
    objects = []
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if esc:
            esc = False
            continue
        if ch == "\\" and in_str:
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                obj_str = text[start : i + 1]
                try:
                    obj = json.loads(_repair_json(obj_str))
                    objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = -1
    return objects


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
    
    get_client().update_current_span(input={"seed_task": seed_task, "num_variants": num_variants})

    prompt = f"""Generate {num_variants} variations of this evaluation task.
Change the firmographics, numbers, and signal strength but keep the exact same failure dimension.
Do not change the core structure.
Return exactly a JSON array containing the {num_variants} variation objects.

FIRMOGRAPHIC CONSISTENCY RULES (critical — judge will score coherence):
- employee_count must be consistent with the funding stage and company age
  (seed-stage: <20 employees; Series A: 20-100; Series B: 100-500; Series C+: 500+)
- funding amount must match the stage label (seed: $500K-$3M; A: $5M-$20M; B: $20M-$80M)
- do NOT mix signals (e.g., "500 employees" with "just raised seed round")
- closed_at date must be within the last 24 months (2024-01 to 2026-04)
- Use realistic company names and domains that match each other

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
            "max_tokens": 32000,
        },
    )

    res_json = response.json()
    if "error" in res_json:
        raise Exception(f"OpenRouter API error: {res_json['error']}")

    try:
        msg = res_json["choices"][0]["message"]
        # Thinking models return content=null; fall back to reasoning_content
        content = msg.get("content") or msg.get("reasoning_content") or ""
        if not content:
            raise ValueError(f"Empty content from {model}. Full response: {res_json}")
        content = content.strip()
        usage = res_json.get("usage") or {}
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        rates = config["families"]["qwen"]["cost_per_1k_tokens"]
        cost = (tokens_in / 1000.0 * rates["input"]) + (tokens_out / 1000.0 * rates["output"])
        log_cost("bulk_variation", "generate_variations", model, tokens_in, tokens_out, cost)

        parsed = _extract_partial_array(content)
        # Handle {"variations": [...]} wrapper that slipped through
        if len(parsed) == 1 and isinstance(parsed[0], dict):
            for v in parsed[0].values():
                if isinstance(v, list):
                    parsed = v
                    break

        get_client().update_current_span(output=parsed)
        return parsed
    except Exception as e:
        get_client().update_current_span(output={"error": str(e)})
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
