import json

from config import STATE_FILE


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed": {}}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def is_processed(state: dict, job_id: str) -> bool:
    return job_id in state.get("processed", {})


def mark_processed(state: dict, job_id: str, result: dict):
    state.setdefault("processed", {})[job_id] = result
