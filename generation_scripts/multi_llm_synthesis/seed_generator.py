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


def get_router_config() -> dict:
    path = os.path.join(os.path.dirname(__file__), "..", "router_config.json")
    with open(path, "r") as f:
        return json.load(f)


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


def _extract_json(text: str) -> dict:
    """Extract a JSON object from model output, tolerating markdown and bad escaping."""
    text = text.strip()
    if not text:
        raise ValueError("Empty response from model")
    # Strip ```json ... ``` fencing
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    # Find first { in case there's preamble
    brace = text.find("{")
    if brace > 0:
        text = text[brace:]
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try after repairing unescaped control characters
    try:
        return json.loads(_repair_json(text))
    except json.JSONDecodeError:
        pass
    # Last resort: truncate to last valid top-level closing brace
    depth = 0
    last_valid_end = -1
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
        if not in_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    last_valid_end = i
    if last_valid_end > 0:
        return json.loads(_repair_json(text[: last_valid_end + 1]))
    raise ValueError(f"Could not extract valid JSON from model output (len={len(text)})")


@observe()
def generate_seed_task(taxonomy: str, rubric: str) -> dict:
    """Generate a single seed task from a Frontier model."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    config = get_router_config()
    model = config["families"]["anthropic"]["models"][0]

    get_client().update_current_span(input={"taxonomy": taxonomy, "rubric": rubric})

    prompt = (
        "Generate a hard evaluation case for a B2B sales agent.\n\n"
        f"Failure taxonomy: {taxonomy}\n\n"
        f"Rubric dimensions: {rubric}\n\n"
        "Generate ONE task as a JSON object with these keys:\n"
        "  input_context: {prospect_brief, bench_summary, prior_thread}\n"
        "  candidate_output: string (email that looks correct but violates one dimension)\n"
        "  ground_truth: {banned_phrases, required_phrases, correct_segment}\n"
        "  metadata: {category, difficulty}\n\n"
        "Use realistic Crunchbase-style firmographics. "
        "Return ONLY the JSON object, no markdown fencing."
    )

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://localhost:3000",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 4000,
        },
    )

    res_json = response.json()
    if "error" in res_json:
        raise Exception(f"OpenRouter API error: {res_json['error']}")

    try:
        content = res_json["choices"][0]["message"]["content"]
        usage = res_json.get("usage") or {}
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        rates = config["families"]["anthropic"]["cost_per_1k_tokens"]
        cost = (tokens_in / 1000.0 * rates["input"]) + (tokens_out / 1000.0 * rates["output"])
        log_cost("seed_generation", "generate_seed", model, tokens_in, tokens_out, cost)

        task_data = _extract_json(content)
        task_data.setdefault("metadata", {})["source_mode"] = "multi-llm-synthesis"
        get_client().update_current_span(output=task_data)
        return task_data
    except Exception as e:
        get_client().update_current_span(output={"error": str(e)})
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
