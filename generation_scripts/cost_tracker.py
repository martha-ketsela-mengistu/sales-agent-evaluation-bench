import json
import os
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "cost_log.json"

class BudgetExceededError(Exception):
    pass

def get_running_total() -> float:
    if not LOG_FILE.exists():
        return 0.0
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
            return data.get("total_spend", 0.0)
    except json.JSONDecodeError:
        return 0.0

def log_cost(bucket: str, purpose: str, model: str, tokens_in: int, tokens_out: int, cost: float):
    running_total = get_running_total() + cost
    
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "bucket": bucket,
        "purpose": purpose,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
        "running_total": running_total
    }
    
    # Read existing
    data = {"total_spend": 0.0, "budget_limit": 10.00, "currency": "USD", "entries": []}
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass
            
    data["total_spend"] = running_total
    data["entries"].append(entry)
    
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)
    
    # Check budget based on cost.md (Act II budget limit = $5.00)
    if running_total > 5.00:
        raise BudgetExceededError(f"Act II budget exceeded: ${running_total:.2f}")
