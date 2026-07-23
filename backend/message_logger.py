"""
Single choke-point for persisting agent messages, role-labeled.

Every agent path (orchestrator, RAG, web search, evaluator, gap updater, eval
table, answer assist, scenario generator, suggestions, and the user-facing
response) logs through here so a conversation holds a full, auditable trail of
both internal and user-facing messages.

`internal=True` marks messages that should not be shown in the chat transcript
(they still get persisted). The frontend renders only user_message/response_message.
"""

from typing import Any, Dict, Optional

from backend.db import repo

# Canonical roles (free-form text column, listed here for consistency).
ROLE_USER = "user_message"
ROLE_RESPONSE = "response_message"
ROLE_ORCHESTRATOR = "orchestrator"
ROLE_RAG = "rag_agent"
ROLE_WEB_SEARCH = "web_search"
ROLE_EVALUATOR = "evaluator"
ROLE_GAP_UPDATER = "gap_updater"
ROLE_EVAL_TABLE = "eval_table"
ROLE_ANSWER_ASSIST = "answer_assist"
ROLE_SCENARIO_GEN = "scenario_generator"
ROLE_SUGGESTIONS = "suggestions"


def log_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    internal: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    meta = dict(metadata or {})
    meta["internal"] = internal
    return repo.add_message(conversation_id, role, content, meta)
