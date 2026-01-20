from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Feedback_Chat_Agent"
if not os.getenv("LANGCHAIN_API_KEY"):
    print("⚠️  Warning: LANGCHAIN_API_KEY not found in .env file. LangSmith tracing will be disabled.")

sys.path.append(str(Path(__file__).parent.parent))

from trainings_2_experts import training_1, training_2, training_3, training_objectives
from backend.evaluator import run_evaluations
from backend.chat_agent import ChatAgent

app = FastAPI(title="Learner Feedback Chat System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store evaluations in memory (in production, use a database)
evaluations_store: Dict[str, Any] = {}
chat_agents: Dict[str, ChatAgent] = {}


class ChatMessage(BaseModel):
    session_id: str
    message: str
    web_search_enabled: bool = False


class ChatResponse(BaseModel):
    response: str
    has_code: bool = False
    code: Optional[str] = None
    code_output: Optional[str] = None
    citations: List[Dict[str, str]] = []


@app.get("/")
async def root():
    return {"message": "Learner Feedback Chat System API"}


@app.get("/trainings")
async def get_trainings():
    """Get all training modules"""
    trainings = [
        {
            "id": "training_1",
            "name": "Module 1: Diagnostic et suivi de la migraine",
            "content": training_1,
            "objectives": training_objectives
        },
        {
            "id": "training_2",
            "name": "Module 2: Traitement aigu et gestion des habitudes de vie de la migraine",
            "content": training_2,
            "objectives": training_objectives
        },
        {
            "id": "training_3",
            "name": "Module 3: Traitement préventif de la migraine",
            "content": training_3,
            "objectives": training_objectives
        }
    ]
    return {"trainings": trainings}


@app.post("/evaluate")
async def evaluate_trainings():
    """Run evaluations on all training modules"""
    try:
        evaluations = run_evaluations()
        session_id = "session_" + str(len(evaluations_store) + 1)
        evaluations_store[session_id] = evaluations
        return {
            "session_id": session_id,
            "status": "completed",
            "evaluations": evaluations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluation/{session_id}")
async def get_evaluation(session_id: str):
    """Get evaluation results for a session"""
    if session_id not in evaluations_store:
        raise HTTPException(status_code=404, detail="Session not found")
    return evaluations_store[session_id]


@app.post("/chat")
async def chat(message: ChatMessage):
    """Chat with the feedback agent"""
    try:
        print(f"\n{'='*70}")
        print(f"📨 INCOMING REQUEST:")
        print(f"   Session ID: {message.session_id}")
        print(f"   Message: {message.message[:100]}")
        print(f"   Web Search: {message.web_search_enabled}")
        print(f"{'='*70}\n")

        # Get or create chat agent for this session
        if message.session_id not in chat_agents:
            if message.session_id not in evaluations_store:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found. Please run evaluation first."
                )
            chat_agents[message.session_id] = ChatAgent(
                evaluations=evaluations_store[message.session_id]
            )

        agent = chat_agents[message.session_id]
        response = agent.chat(message.message, web_search_enabled=message.web_search_enabled)

        # Log response details
        print(f"\n{'='*70}")
        print(f"📤 OUTGOING RESPONSE:")
        print(f"   Has code: {response.get('has_code', False)}")
        if response.get('code_output'):
            code_output_preview = str(response.get('code_output'))[:200]
            print(f"   Code output (first 200 chars): {code_output_preview}...")
            print(f"   Code output type: {type(response.get('code_output'))}")
        citations = response.get('citations') or []
        print(f"   Citations count: {len(citations)}")
        print(f"{'='*70}\n")

        return ChatResponse(
            response=response.get("response", ""),
            has_code=response.get("has_code", False),
            code=response.get("code"),
            code_output=response.get("code_output"),
            citations=response.get("citations", [])
        )
    except Exception as e:
        print(f"❌ ERROR in /chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/reset/{session_id}")
async def reset_chat(session_id: str):
    """Reset chat history for a session"""
    if session_id in chat_agents:
        del chat_agents[session_id]
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
