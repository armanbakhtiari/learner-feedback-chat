"""
File-based Session Store with TTL

Persists session data (evaluations and chat history) to disk so that
sessions survive container restarts on Replit Cloud Run.
Sessions expire after 2 hours of inactivity.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

# Store sessions in a directory that persists across restarts
SESSIONS_DIR = Path(__file__).parent.parent / ".sessions"
SESSION_TTL_SECONDS = 2 * 60 * 60  # 2 hours


def _ensure_dir():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    """Get the file path for a session"""
    # Sanitize session_id to prevent path traversal
    safe_id = session_id.replace("/", "_").replace("..", "_")
    return SESSIONS_DIR / f"{safe_id}.json"


def save_session(session_id: str, evaluations: Dict[str, Any], training_type: str = "migraine"):
    """Save evaluation data for a session"""
    _ensure_dir()
    data = {
        "session_id": session_id,
        "evaluations": evaluations,
        "training_type": training_type,
        "created_at": time.time(),
        "last_accessed": time.time(),
        "chat_history": []
    }
    path = _session_path(session_id)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Load session data, returns None if expired or not found"""
    path = _session_path(session_id)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Check TTL
    last_accessed = data.get("last_accessed", 0)
    if time.time() - last_accessed > SESSION_TTL_SECONDS:
        # Session expired, clean up
        try:
            path.unlink()
        except OSError:
            pass
        return None

    # Update last_accessed
    data["last_accessed"] = time.time()
    try:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass

    return data


def save_chat_history(session_id: str, history: List[Dict[str, str]]):
    """Save conversation history for a session"""
    path = _session_path(session_id)
    if not path.exists():
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["chat_history"] = history
        data["last_accessed"] = time.time()
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except (json.JSONDecodeError, OSError):
        pass


def get_chat_history(session_id: str) -> List[Dict[str, str]]:
    """Load conversation history for a session"""
    session = get_session(session_id)
    if session is None:
        return []
    return session.get("chat_history", [])


def delete_session_chat(session_id: str):
    """Delete only chat history (keep evaluations)"""
    path = _session_path(session_id)
    if not path.exists():
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["chat_history"] = []
        data["last_accessed"] = time.time()
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except (json.JSONDecodeError, OSError):
        pass


def cleanup_expired_sessions():
    """Remove all expired session files"""
    _ensure_dir()
    now = time.time()
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            last_accessed = data.get("last_accessed", 0)
            if now - last_accessed > SESSION_TTL_SECONDS:
                path.unlink()
        except (json.JSONDecodeError, OSError):
            # Remove corrupted files
            try:
                path.unlink()
            except OSError:
                pass


def generate_session_id() -> str:
    """Generate a unique session ID"""
    import uuid
    return f"session_{uuid.uuid4().hex[:12]}"
