"""
Repository helpers over Supabase (service_role). Grouped by domain.

These are thin, typed accessors used by the FastAPI endpoints, the completion
pipeline, and the agents. All writes go through here so the backend stays the
single source of truth. Nothing here ever returns expert responses to a client
path — expert data is only read by the evaluator (`get_experts_for_training`).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from backend.db.client import get_supabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


# ============================== users / bootstrap ==============================

def get_user_by_clerk_id(clerk_user_id: str) -> Optional[Dict[str, Any]]:
    sb = get_supabase()
    rows = sb.table("users").select("*").eq("clerk_user_id", clerk_user_id).limit(1).execute().data
    return rows[0] if rows else None


def create_user(clerk_user_id: str, email: Optional[str], full_name: Optional[str]) -> Dict[str, Any]:
    sb = get_supabase()
    return (
        sb.table("users")
        .insert({"clerk_user_id": clerk_user_id, "email": email, "full_name": full_name})
        .execute()
    ).data[0]


def upsert_user(clerk_user_id: str, email: Optional[str], full_name: Optional[str]) -> Dict[str, Any]:
    existing = get_user_by_clerk_id(clerk_user_id)
    if existing:
        return existing
    return create_user(clerk_user_id, email, full_name)


def get_mandatory_training() -> Optional[Dict[str, Any]]:
    sb = get_supabase()
    rows = sb.table("trainings").select("*").eq("origin", "seed_mandatory").limit(1).execute().data
    return rows[0] if rows else None


def ensure_bootstrap(user: Dict[str, Any]) -> None:
    """On first sign-in: assign the mandatory training + create an empty gap doc."""
    sb = get_supabase()
    user_id = user["id"]

    # Empty learning-gap doc.
    gap = sb.table("learning_gaps").select("id").eq("user_id", user_id).limit(1).execute().data
    if not gap:
        sb.table("learning_gaps").insert({"user_id": user_id, "content": "", "structured": {}}).execute()

    # Mandatory training assignment.
    mandatory = get_mandatory_training()
    if mandatory:
        assign_training(user_id, mandatory["id"])


# ============================== trainings / content ============================

def get_user_training(user_training_id: str) -> Optional[Dict[str, Any]]:
    sb = get_supabase()
    rows = sb.table("user_trainings").select("*").eq("id", user_training_id).limit(1).execute().data
    return rows[0] if rows else None


def get_training(training_id: str) -> Optional[Dict[str, Any]]:
    if not _is_uuid(training_id):
        return None
    sb = get_supabase()
    rows = sb.table("trainings").select("*").eq("id", training_id).limit(1).execute().data
    return rows[0] if rows else None


def _situations_with_scenarios(training_id: str, include_experts: bool) -> List[Dict[str, Any]]:
    sb = get_supabase()
    situations = (
        sb.table("situations").select("*").eq("training_id", training_id)
        .order("situation_index").execute().data
    )
    for sit in situations:
        scenarios = (
            sb.table("scenarios").select("*").eq("situation_id", sit["id"])
            .order("scenario_index").execute().data
        )
        if include_experts:
            for sc in scenarios:
                sc["experts"] = (
                    sb.table("expert_responses").select("expert_label,likert,justification")
                    .eq("scenario_id", sc["id"]).execute().data
                )
        sit["scenarios"] = scenarios
    return situations


def get_training_content(training_id: str, include_experts: bool = False) -> Dict[str, Any]:
    """Full training with nested situations/scenarios (experts only when asked)."""
    training = get_training(training_id)
    if not training:
        return {}
    training["situations"] = _situations_with_scenarios(training_id, include_experts)
    return training


def list_bank_trainings() -> List[Dict[str, Any]]:
    """
    Shared suggestion bank = trainings with origin seed_bank / suggested_bank, each
    flattened to {id, title, domain, objectives, content} where content is the
    concatenated situation text. Used to (re)build the bank vector store.
    """
    sb = get_supabase()
    bank = (
        sb.table("trainings").select("id,title,domain,learning_objectives,origin")
        .in_("origin", ["seed_bank", "suggested_bank"]).order("created_at").execute().data
    )
    out: List[Dict[str, Any]] = []
    for tr in bank:
        sits = sb.table("situations").select("text").eq("training_id", tr["id"]).order("situation_index").execute().data
        out.append({
            "id": tr["id"],
            "title": tr["title"],
            "domain": tr.get("domain", ""),
            "objectives": tr.get("learning_objectives", []),
            "content": "\n\n".join(s["text"] for s in sits),
        })
    return out


def bank_hash() -> str:
    """Stable hash of the bank content, so the vector store re-indexes only on change."""
    import hashlib
    payload = "".join(f"{b['id']}:{len(b['content'])}:{b['title']}" for b in list_bank_trainings())
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_training(title: str, domain: str, origin: str, objectives: List[str],
                    created_by: Optional[str] = None, source_training_id: Optional[str] = None) -> Dict[str, Any]:
    sb = get_supabase()
    return (
        sb.table("trainings")
        .insert({
            "title": title, "domain": domain, "origin": origin,
            "learning_objectives": objectives,
            "created_by": created_by, "source_training_id": source_training_id,
        })
        .execute()
    ).data[0]


def add_situation(training_id: str, situation_index: int, title: str, text: str) -> Dict[str, Any]:
    sb = get_supabase()
    return sb.table("situations").insert({
        "training_id": training_id, "situation_index": situation_index, "title": title, "text": text,
    }).execute().data[0]


def add_scenario(situation_id: str, scenario_index: int, hypothesis: str, new_information: str) -> Dict[str, Any]:
    sb = get_supabase()
    return sb.table("scenarios").insert({
        "situation_id": situation_id, "scenario_index": scenario_index,
        "hypothesis": hypothesis, "new_information": new_information,
    }).execute().data[0]


def add_expert_responses(scenario_id: str, experts: List[Dict[str, Any]]) -> None:
    sb = get_supabase()
    rows = [{
        "scenario_id": scenario_id,
        "expert_label": e["expert_label"], "likert": e["likert"], "justification": e["justification"],
    } for e in experts]
    if rows:
        sb.table("expert_responses").insert(rows).execute()


def get_scenario_with_situation(scenario_id: str) -> Optional[Dict[str, Any]]:
    """A scenario + its parent situation (NO experts) — for the answer-assist agent."""
    sb = get_supabase()
    rows = sb.table("scenarios").select("*").eq("id", scenario_id).limit(1).execute().data
    if not rows:
        return None
    scenario = rows[0]
    sit = sb.table("situations").select("*").eq("id", scenario["situation_id"]).limit(1).execute().data
    scenario["situation"] = sit[0] if sit else None
    return scenario


# ============================== user_trainings ================================

def assign_training(user_id: str, training_id: str) -> Dict[str, Any]:
    """Create a user_training if the user doesn't already have one for this training."""
    sb = get_supabase()
    existing = (
        sb.table("user_trainings").select("*")
        .eq("user_id", user_id).eq("training_id", training_id).limit(1).execute().data
    )
    if existing:
        return existing[0]
    return (
        sb.table("user_trainings")
        .insert({"user_id": user_id, "training_id": training_id, "status": "not_started"})
        .execute()
    ).data[0]


def _decorate_with_training(user_trainings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sb = get_supabase()
    for ut in user_trainings:
        tr = get_training(ut["training_id"]) or {}
        ut["training"] = tr
        sits = sb.table("situations").select("title,situation_index").eq(
            "training_id", ut["training_id"]).order("situation_index").execute().data
        ut["situation_titles"] = [s["title"] for s in sits]
    return user_trainings


def list_dashboard(user_id: str) -> List[Dict[str, Any]]:
    """Assigned trainings not yet completed (mandatory + picked/generated)."""
    sb = get_supabase()
    rows = (
        sb.table("user_trainings").select("*")
        .eq("user_id", user_id).neq("status", "completed")
        .order("created_at").execute().data
    )
    return _decorate_with_training(rows)


def list_completed(user_id: str) -> List[Dict[str, Any]]:
    sb = get_supabase()
    rows = (
        sb.table("user_trainings").select("*")
        .eq("user_id", user_id).eq("status", "completed")
        .order("completed_at", desc=True).execute().data
    )
    rows = _decorate_with_training(rows)
    for ut in rows:
        ev = get_evaluation(ut["id"])
        ut["evaluation_html"] = ev.get("evaluation_html") if ev else None
    return rows


def set_status(user_training_id: str, status: str, *, started: bool = False, completed: bool = False) -> None:
    sb = get_supabase()
    patch: Dict[str, Any] = {"status": status}
    if started:
        patch["started_at"] = _now()
    if completed:
        patch["completed_at"] = _now()
    sb.table("user_trainings").update(patch).eq("id", user_training_id).execute()


# ============================== user_responses ===============================

def get_responses(user_training_id: str) -> List[Dict[str, Any]]:
    sb = get_supabase()
    return (
        sb.table("user_responses").select("*")
        .eq("user_training_id", user_training_id).execute().data
    )


def upsert_responses(user_training_id: str, answers: List[Dict[str, Any]]) -> None:
    """answers: [{scenario_id, likert, justification}]. Upsert on (ut, scenario)."""
    sb = get_supabase()
    for a in answers:
        payload = {
            "user_training_id": user_training_id,
            "scenario_id": a["scenario_id"],
            "likert": a.get("likert"),
            "justification": a.get("justification"),
        }
        sb.table("user_responses").upsert(
            payload, on_conflict="user_training_id,scenario_id"
        ).execute()


# ============================== evaluations ==================================

def get_evaluation(user_training_id: str) -> Optional[Dict[str, Any]]:
    sb = get_supabase()
    rows = sb.table("evaluations").select("*").eq("user_training_id", user_training_id).limit(1).execute().data
    return rows[0] if rows else None


def save_evaluation(user_training_id: str, evaluation_json: Dict[str, Any], evaluation_html: Optional[str]) -> Dict[str, Any]:
    sb = get_supabase()
    payload = {
        "user_training_id": user_training_id,
        "evaluation_json": evaluation_json,
        "evaluation_html": evaluation_html,
    }
    return sb.table("evaluations").upsert(payload, on_conflict="user_training_id").execute().data[0]


def update_evaluation_html(user_training_id: str, evaluation_html: str) -> None:
    sb = get_supabase()
    sb.table("evaluations").update({"evaluation_html": evaluation_html}).eq(
        "user_training_id", user_training_id).execute()


# ============================== conversations / messages ======================

def create_conversation(user_id: str, user_training_id: str, title: str) -> Dict[str, Any]:
    sb = get_supabase()
    existing = sb.table("conversations").select("*").eq("user_training_id", user_training_id).limit(1).execute().data
    if existing:
        return existing[0]
    return (
        sb.table("conversations")
        .insert({"user_id": user_id, "user_training_id": user_training_id, "title": title})
        .execute()
    ).data[0]


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    sb = get_supabase()
    rows = sb.table("conversations").select("*").eq("id", conversation_id).limit(1).execute().data
    return rows[0] if rows else None


def list_conversations(user_id: str) -> List[Dict[str, Any]]:
    sb = get_supabase()
    return (
        sb.table("conversations").select("*")
        .eq("user_id", user_id).order("created_at", desc=True).execute().data
    )


def get_messages(conversation_id: str, roles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    sb = get_supabase()
    q = sb.table("messages").select("*").eq("conversation_id", conversation_id)
    if roles:
        q = q.in_("role", roles)
    return q.order("created_at").execute().data


def add_message(conversation_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    sb = get_supabase()
    return (
        sb.table("messages")
        .insert({
            "conversation_id": conversation_id,
            "role": role,
            "content": content or "",
            "metadata": metadata or {},
        })
        .execute()
    ).data[0]


# ============================== learning_gaps ================================

def get_learning_gap(user_id: str) -> Dict[str, Any]:
    sb = get_supabase()
    rows = sb.table("learning_gaps").select("*").eq("user_id", user_id).limit(1).execute().data
    if rows:
        return rows[0]
    return sb.table("learning_gaps").insert({"user_id": user_id}).execute().data[0]


def upsert_learning_gap(user_id: str, content: str, structured: Dict[str, Any]) -> Dict[str, Any]:
    sb = get_supabase()
    existing = sb.table("learning_gaps").select("id").eq("user_id", user_id).limit(1).execute().data
    if existing:
        return (
            sb.table("learning_gaps")
            .update({"content": content, "structured": structured})
            .eq("user_id", user_id).execute()
        ).data[0]
    return (
        sb.table("learning_gaps")
        .insert({"user_id": user_id, "content": content, "structured": structured})
        .execute()
    ).data[0]


# ============================== notifications ================================

def add_notification(user: Dict[str, Any], notif_type: str, title: str, body: Optional[str] = None,
                     user_training_id: Optional[str] = None) -> Dict[str, Any]:
    sb = get_supabase()
    return (
        sb.table("notifications")
        .insert({
            "user_id": user["id"],
            "clerk_user_id": user["clerk_user_id"],
            "type": notif_type,
            "title": title,
            "body": body,
            "user_training_id": user_training_id,
        })
        .execute()
    ).data[0]


def list_notifications(user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
    sb = get_supabase()
    q = sb.table("notifications").select("*").eq("user_id", user_id)
    if unread_only:
        q = q.eq("read", False)
    return q.order("created_at", desc=True).limit(100).execute().data


def mark_notification_read(notification_id: str) -> None:
    sb = get_supabase()
    sb.table("notifications").update({"read": True}).eq("id", notification_id).execute()
