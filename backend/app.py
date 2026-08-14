"""
FastAPI backend for the multi-user SENSAI Feedback Agent.

Backend-mediated auth (Clerk JWT) + Supabase data layer + all agents. The browser
sends a Clerk JWT; the backend verifies it, is the only writer to Supabase, and runs
the completion pipeline in the background. See GCP.md / DEPLOYMENT.md.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "Feedback_Chat_Agent"
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

from backend.auth import get_current_user
from backend.db import repo


# ------------------------------------------------------------------ app
@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="SENSAI Feedback Agent", lifespan=lifespan)

_allowed = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o] or [
    "http://localhost:3000",
    "https://feedback-chat-agent.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ schemas
class ResponseItem(BaseModel):
    scenario_id: str
    likert: Optional[str] = None
    justification: Optional[str] = None


class SaveResponses(BaseModel):
    responses: List[ResponseItem]


class AssistRequest(BaseModel):
    scenario_id: str


class ChatRequest(BaseModel):
    message: str
    web_search_enabled: bool = False


class PickSuggestion(BaseModel):
    training_id: str


class GenerateRequest(BaseModel):
    user_training_id: str


def _own_user_training(user: Dict[str, Any], user_training_id: str) -> Dict[str, Any]:
    ut = repo.get_user_training(user_training_id)
    if not ut or ut["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Training not found")
    return ut


def _own_conversation(user: Dict[str, Any], conversation_id: str) -> Dict[str, Any]:
    conv = repo.get_conversation(conversation_id)
    if not conv or conv["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


# ------------------------------------------------------------------ health
@app.get("/health")
async def health():
    return {"status": "healthy"}


# ------------------------------------------------------------------ user / dashboard
@app.get("/me")
async def me(user: Dict[str, Any] = Depends(get_current_user)):
    repo.ensure_bootstrap(user)  # idempotent safety net
    return {"id": user["id"], "email": user.get("email"), "full_name": user.get("full_name")}


@app.get("/dashboard")
async def dashboard(user: Dict[str, Any] = Depends(get_current_user)):
    return {"trainings": repo.list_dashboard(user["id"])}


@app.get("/completed")
async def completed(user: Dict[str, Any] = Depends(get_current_user)):
    return {"trainings": repo.list_completed(user["id"])}


# ------------------------------------------------------------------ training page
def _strip_expert_material(training: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove everything only the evaluator/feedback agent may see before a client payload.

    `include_experts=False` already omits expert_responses; the situations' educational
    synthesis is the same kind of authored reference material and must not leak either.
    """
    for sit in training.get("situations", []):
        sit.pop("educational_synthesis", None)
    return training


@app.get("/trainings/{user_training_id}")
async def get_training(user_training_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    ut = _own_user_training(user, user_training_id)
    # Client view: NO expert responses, NO educational synthesis.
    training = _strip_expert_material(
        repo.get_training_content(ut["training_id"], include_experts=False)
    )
    responses = {r["scenario_id"]: r for r in repo.get_responses(user_training_id)}
    for sit in training.get("situations", []):
        for sc in sit.get("scenarios", []):
            r = responses.get(sc["id"])
            sc["response"] = {"likert": r.get("likert"), "justification": r.get("justification")} if r else None
    return {"user_training": ut, "training": training}


@app.put("/trainings/{user_training_id}/responses")
async def save_responses(user_training_id: str, body: SaveResponses,
                         user: Dict[str, Any] = Depends(get_current_user)):
    ut = _own_user_training(user, user_training_id)
    if ut["status"] == "completed":
        raise HTTPException(status_code=400, detail="Training already completed")
    repo.upsert_responses(user_training_id, [r.model_dump() for r in body.responses])
    if ut["status"] == "not_started":
        repo.set_status(user_training_id, "in_progress", started=True)
    return {"status": "saved"}


@app.post("/trainings/{user_training_id}/assist")
async def assist(user_training_id: str, body: AssistRequest,
                 user: Dict[str, Any] = Depends(get_current_user)):
    ut = _own_user_training(user, user_training_id)
    scenario = repo.get_scenario_with_situation(body.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    from backend.answer_assist import generate_assisted_answer
    situation_text = (scenario.get("situation") or {}).get("text", "")
    training = repo.get_training(ut["training_id"]) or {}
    return generate_assisted_answer(situation_text, scenario["hypothesis"], scenario["new_information"],
                                    scale=training.get("likert_scale"))


@app.post("/trainings/{user_training_id}/evaluate")
async def evaluate(user_training_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    ut = _own_user_training(user, user_training_id)
    if ut["status"] == "completed":
        raise HTTPException(status_code=400, detail="Training already completed")

    # Require an answer for every scenario before evaluating.
    training = repo.get_training_content(ut["training_id"], include_experts=False)
    scenario_ids = [sc["id"] for sit in training.get("situations", []) for sc in sit.get("scenarios", [])]
    answered = {
        r["scenario_id"] for r in repo.get_responses(user_training_id)
        if r.get("likert") and (r.get("justification") or "").strip()
    }
    missing = [sid for sid in scenario_ids if sid not in answered]
    if missing:
        raise HTTPException(status_code=400,
                            detail=f"{len(missing)} scénario(s) sans réponse complète.")

    repo.set_status(user_training_id, "completed", completed=True)

    from backend.pipeline import run_completion_pipeline
    await asyncio.to_thread(run_completion_pipeline, user, user_training_id)
    return {"status": "completed", "user_training_id": user_training_id}


# ------------------------------------------------------------------ conversations / chat
@app.get("/conversations")
async def conversations(user: Dict[str, Any] = Depends(get_current_user)):
    return {"conversations": repo.list_conversations(user["id"])}


@app.get("/conversations/{conversation_id}/messages")
async def conversation_messages(conversation_id: str, include_internal: bool = False,
                                user: Dict[str, Any] = Depends(get_current_user)):
    _own_conversation(user, conversation_id)
    roles = None if include_internal else ["user_message", "response_message"]
    return {"messages": repo.get_messages(conversation_id, roles=roles)}


@app.post("/conversations/{conversation_id}/chat")
async def conversation_chat(conversation_id: str, body: ChatRequest,
                            user: Dict[str, Any] = Depends(get_current_user)):
    conv = _own_conversation(user, conversation_id)
    ut = repo.get_user_training(conv["user_training_id"])
    evaluation = repo.get_evaluation(conv["user_training_id"])
    if not evaluation:
        raise HTTPException(status_code=400, detail="Evaluation not ready for this conversation")

    training = repo.get_training(ut["training_id"]) or {}
    objectives = training.get("learning_objectives") or []
    objectives_str = "\n".join(f"- {o}" for o in objectives)
    gap = repo.get_learning_gap(user["id"]).get("content", "")

    # Rehydrate chat history (user + response messages only).
    from langchain_core.messages import HumanMessage, AIMessage
    history = []
    for m in repo.get_messages(conversation_id, roles=["user_message", "response_message"]):
        if m["role"] == "user_message":
            history.append(HumanMessage(content=m["content"]))
        else:
            history.append(AIMessage(content=m["content"]))

    from backend.chat_agent import ChatAgent
    # Same as the pipeline: the training's domain selects the knowledge base, so follow-up
    # questions are never answered from another domain's reference PDFs.
    agent = ChatAgent(evaluation["evaluation_json"], objectives_str, learning_gap=gap,
                      conversation_history=history,
                      training_type=training.get("domain") or "migraine")
    result = agent.chat(body.message, web_search_enabled=body.web_search_enabled,
                        conversation_id=conversation_id)
    return result


# ------------------------------------------------------------------ learning gaps
@app.get("/learning-gaps")
async def learning_gaps(user: Dict[str, Any] = Depends(get_current_user)):
    gap = repo.get_learning_gap(user["id"])
    return {"content": gap.get("content", ""), "structured": gap.get("structured", {}),
            "updated_at": gap.get("updated_at")}


@app.get("/learning-gaps/history")
async def learning_gaps_history(user: Dict[str, Any] = Depends(get_current_user)):
    """Previous versions of the learner's profile, newest first (one per evaluation)."""
    return {"history": repo.list_learning_gap_history(user["id"])}


# ------------------------------------------------------------------ notifications
@app.get("/notifications")
async def notifications(unread_only: bool = False, user: Dict[str, Any] = Depends(get_current_user)):
    return {"notifications": repo.list_notifications(user["id"], unread_only=unread_only)}


@app.post("/notifications/{notification_id}/read")
async def read_notification(notification_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    repo.mark_notification_read(notification_id)
    return {"status": "read"}


# ------------------------------------------------------------------ suggestions
@app.get("/completed-list")
async def completed_list(user: Dict[str, Any] = Depends(get_current_user)):
    """Lightweight list of completed trainings (for the suggestions page; no LLM)."""
    return {
        "completed": [
            {"user_training_id": c["id"], "title": (c.get("training") or {}).get("title", "")}
            for c in repo.list_completed(user["id"])
        ]
    }


@app.get("/bank-trainings/{training_id}")
async def bank_training_preview(training_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Read-only preview of a shared training, so a learner can see what a suggestion
    actually contains before adding it to their dashboard.

    Limited to shared catalogue trainings — a user's own generated trainings are not
    enumerable through here. Carries no expert responses and no educational synthesis.
    """
    training = repo.get_training(training_id)
    if not training or training.get("origin") not in ("seed_bank", "suggested_bank", "seed_mandatory"):
        raise HTTPException(status_code=404, detail="Training not found")

    content = _strip_expert_material(repo.get_training_content(training_id, include_experts=False))
    return {
        "id": content["id"],
        "title": content["title"],
        "learning_objectives": content.get("learning_objectives") or [],
        "situations": [
            {
                "title": sit.get("title"),
                "text": sit.get("text", ""),
                "scenarios": [
                    {"hypothesis": sc.get("hypothesis", ""), "new_information": sc.get("new_information", "")}
                    for sc in sit.get("scenarios", [])
                ],
            }
            for sit in content.get("situations", [])
        ],
    }


@app.get("/suggestions")
async def suggestions(preference: str = "", user: Dict[str, Any] = Depends(get_current_user)):
    """`preference` is the learner's optional free-text wish; empty = gap-profile only."""
    completed = [
        {"user_training_id": c["id"], "title": (c.get("training") or {}).get("title", "")}
        for c in repo.list_completed(user["id"])
    ]
    # No suggestions until at least one training is completed (nothing to base them on).
    if not completed:
        return {"status": "no_completed", "suggestions": [], "completed": []}

    gap = repo.get_learning_gap(user["id"]).get("content", "")
    from backend.suggestions import suggest_bank_trainings
    result = suggest_bank_trainings(user["id"], gap, preference=preference[:300])
    result["completed"] = completed
    return result


@app.post("/suggestions/pick")
async def pick_suggestion(body: PickSuggestion, user: Dict[str, Any] = Depends(get_current_user)):
    training = repo.get_training(body.training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Training not found")
    ut = repo.assign_training(user["id"], body.training_id)
    return {"status": "assigned", "user_training_id": ut["id"]}


@app.post("/suggestions/generate")
async def generate_suggestion(body: GenerateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """Path 2: generate a NEW training from a completed one's situation(s), gap-focused."""
    ut = _own_user_training(user, body.user_training_id)
    if ut["status"] != "completed":
        raise HTTPException(status_code=400, detail="Select a completed training")

    source = repo.get_training_content(ut["training_id"], include_experts=False)
    objectives = source.get("learning_objectives") or []
    objectives_str = "\n".join(f"- {o}" for o in objectives)
    gap = repo.get_learning_gap(user["id"])
    gaps = (gap.get("structured") or {}).get("objectives", [])

    from backend.scenario_generator import generate_scenarios_for_situation
    from backend.expert_panel_agent import generate_expert_panel

    scale = source.get("likert_scale") or "concordance"
    new_training = repo.create_training(
        title=f"{source['title']} — nouveaux scénarios",
        domain=source.get("domain", "migraine"),
        origin="generated",
        objectives=objectives,
        created_by=user["id"],
        source_training_id=source["id"],
        likert_scale=scale,
    )
    for s_i, sit in enumerate(source.get("situations", []), start=1):
        new_sit = repo.add_situation(new_training["id"], s_i, sit.get("title"), sit["text"],
                                     educational_synthesis=sit.get("educational_synthesis"))
        try:
            generated = generate_scenarios_for_situation(sit, objectives_str, gaps).scenarios
        except Exception as e:
            print(f"⚠️  scenario generation failed: {e}")
            generated = []
        for c_i, sc in enumerate(generated, start=1):
            scenario = repo.add_scenario(new_sit["id"], c_i, sc.hypothesis, sc.new_information)
            try:
                panel = generate_expert_panel(sit["text"], sc.hypothesis, sc.new_information, scale=scale)
                repo.add_expert_responses(scenario["id"], panel)
            except Exception as e:
                print(f"⚠️  expert panel failed: {e}")

    assigned = repo.assign_training(user["id"], new_training["id"])
    return {"status": "created", "training_id": new_training["id"], "user_training_id": assigned["id"],
            "title": new_training["title"]}
