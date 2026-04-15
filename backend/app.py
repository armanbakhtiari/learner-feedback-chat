import sys
import time

_startup_time = time.time()

def _log(msg):
    elapsed = time.time() - _startup_time
    print(f"[STARTUP +{elapsed:.2f}s] {msg}", flush=True)

_log("BEGIN module import")

_log("importing fastapi...")
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
_log("importing CORSMiddleware...")
from fastapi.middleware.cors import CORSMiddleware
_log("importing FileResponse, JSONResponse...")
from fastapi.responses import FileResponse, JSONResponse
_log("importing pydantic...")
from pydantic import BaseModel
_log("importing typing...")
from typing import List, Dict, Any, Optional
_log("importing json, os, pathlib...")
import os
from pathlib import Path
_log("importing dotenv...")
from dotenv import load_dotenv
_log("all imports done")

_log("calling load_dotenv()...")
load_dotenv()
_log("load_dotenv() done")

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Feedback_Chat_Agent"
if not os.getenv("LANGCHAIN_API_KEY"):
    _log("WARNING: LANGCHAIN_API_KEY not found")

sys.path.append(str(Path(__file__).parent.parent))

# Import session store
from backend.session_store import (
    save_session, get_session, save_chat_history,
    delete_session_chat, cleanup_expired_sessions, generate_session_id
)

# Lazy imports - only import heavy modules when needed
_training_data_cache = {}
_evaluator_module = None
_chat_agent_class = None


def get_training_data(training_type: str = "migraine"):
    """Lazy load training data based on training type"""
    global _training_data_cache
    if training_type not in _training_data_cache:
        if training_type == "migraine":
            from trainings_2_experts import training_1, training_2, training_3, training_objectives
            _training_data_cache[training_type] = {
                "trainings": {"training_1": training_1, "training_2": training_2, "training_3": training_3},
                "objectives": training_objectives
            }
        elif training_type == "nursing_1st":
            from trainings_nursing_1stLearner import training_1, training_objectives
            _training_data_cache[training_type] = {
                "trainings": {"training_1": training_1},
                "objectives": training_objectives
            }
        elif training_type == "nursing_2nd":
            from trainings_nursing_2ndLearner import training_1, training_objectives
            _training_data_cache[training_type] = {
                "trainings": {"training_1": training_1},
                "objectives": training_objectives
            }
        elif training_type == "leadership_1st":
            from trainings_leadership_1srLearner import training_1, training_objectives
            _training_data_cache[training_type] = {
                "trainings": {"training_1": training_1},
                "objectives": training_objectives
            }
        elif training_type == "leadership_2nd":
            from trainings_leadership_2ndLearner import training_1, training_objectives
            _training_data_cache[training_type] = {
                "trainings": {"training_1": training_1},
                "objectives": training_objectives
            }
        elif training_type == "leadership_3rd":
            from trainings_leadership_3rdLearner import training_1, training_objectives
            _training_data_cache[training_type] = {
                "trainings": {"training_1": training_1},
                "objectives": training_objectives
            }
        else:
            raise ValueError(f"Unknown training type: {training_type}")
    return _training_data_cache[training_type]


def get_evaluator():
    """Lazy load evaluator module"""
    global _evaluator_module
    if _evaluator_module is None:
        from backend.evaluator import run_evaluations
        _evaluator_module = run_evaluations
    return _evaluator_module


def get_chat_agent_class():
    """Lazy load ChatAgent class"""
    global _chat_agent_class
    if _chat_agent_class is None:
        from backend.chat_agent import ChatAgent
        _chat_agent_class = ChatAgent
    return _chat_agent_class


# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    _log("FastAPI startup - app is ready!")
    cleanup_expired_sessions()
    yield

_log("creating FastAPI app...")
app = FastAPI(title="Learner Feedback Chat System", lifespan=lifespan)
_log("FastAPI app created")

_log("adding CORS middleware...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_log("CORS middleware added")

# In-memory cache for chat agents (recreated from disk if missing)
chat_agents: Dict[str, Any] = {}


class EvaluateRequest(BaseModel):
    training_type: str = "migraine"


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
    total_tokens: int = 0


_log("defining routes...")


# API Routes (must come before static file serving)


@app.get("/trainings")
async def get_trainings(training_type: str = "migraine"):
    """Get training modules for the selected training type"""
    data = get_training_data(training_type)
    trainings_dict = data["trainings"]
    objectives = data["objectives"]

    trainings = []
    if training_type == "migraine":
        names = {
            "training_1": "Module 1: Diagnostic et suivi de la migraine",
            "training_2": "Module 2: Traitement aigu et gestion des habitudes de vie de la migraine",
            "training_3": "Module 3: Traitement preventif de la migraine"
        }
    elif training_type in ("nursing_1st", "nursing_2nd"):
        names = {
            "training_1": "Module 1: Leadership et collaboration en soins infirmiers"
        }
    elif training_type in ("leadership_1st", "leadership_2nd", "leadership_3rd"):
        names = {
            "training_1": "Module 1: Leadership et prise de decision"
        }
    else:
        names = {}

    for tid, content in trainings_dict.items():
        trainings.append({
            "id": tid,
            "name": names.get(tid, tid),
            "content": content,
            "objectives": objectives
        })

    return {"trainings": trainings, "training_type": training_type}


@app.post("/evaluate")
async def evaluate_trainings(request: EvaluateRequest):
    """Run evaluations on training modules for the selected training type"""
    try:
        training_type = request.training_type
        run_evaluations = get_evaluator()
        evaluations = run_evaluations(training_type)
        session_id = generate_session_id()

        # Persist to disk
        save_session(session_id, evaluations, training_type)

        return {
            "session_id": session_id,
            "status": "completed",
            "evaluations": evaluations,
            "training_type": training_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluation/{session_id}")
async def get_evaluation(session_id: str):
    """Get evaluation results for a session"""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return session["evaluations"]


@app.post("/chat")
async def chat(message: ChatMessage):
    """Chat with the feedback agent"""
    try:
        print(f"\n{'='*70}")
        print(f"INCOMING REQUEST:")
        print(f"   Session ID: {message.session_id}")
        print(f"   Message: {message.message[:100]}")
        print(f"   Web Search: {message.web_search_enabled}")
        print(f"{'='*70}\n")

        # Get or create chat agent for this session
        if message.session_id not in chat_agents:
            # Try to load session from disk
            session = get_session(message.session_id)
            if session is None:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found or expired. Please run evaluation first."
                )

            ChatAgent = get_chat_agent_class()
            training_type = session.get("training_type", "migraine")
            agent = ChatAgent(
                evaluations=session["evaluations"],
                training_type=training_type
            )

            # Restore chat history from disk
            stored_history = session.get("chat_history", [])
            if stored_history:
                from langchain_core.messages import HumanMessage, AIMessage
                for msg in stored_history:
                    if msg["role"] == "human":
                        agent.conversation_history.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "ai":
                        agent.conversation_history.append(AIMessage(content=msg["content"]))
                agent.initial_feedback_given = True
                print(f"   Restored {len(stored_history)} messages from disk")

            chat_agents[message.session_id] = agent

        agent = chat_agents[message.session_id]
        response = agent.chat(message.message, web_search_enabled=message.web_search_enabled)

        # Persist chat history to disk
        from langchain_core.messages import HumanMessage as HM
        serialized_history = []
        for msg in agent.conversation_history:
            if hasattr(msg, 'content'):
                role = "human" if isinstance(msg, HM) else "ai"
                serialized_history.append({"role": role, "content": msg.content})
        save_chat_history(message.session_id, serialized_history)

        # Log response details
        print(f"\n{'='*70}")
        print(f"OUTGOING RESPONSE:")
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
            citations=response.get("citations", []),
            total_tokens=response.get("total_tokens", 0)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/reset/{session_id}")
async def reset_chat(session_id: str):
    """Reset chat history for a session"""
    if session_id in chat_agents:
        del chat_agents[session_id]
    delete_session_chat(session_id)
    return {"status": "reset"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    _log("GET /health hit")
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint - serves frontend or health check"""
    index_file = FRONTEND_DIR / "index.html"
    _log(f"GET / - FRONTEND_DIR={FRONTEND_DIR}, exists={FRONTEND_DIR.exists()}, index_exists={index_file.exists()}, resolved={index_file.resolve()}")
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"status": "healthy", "message": "Application is running"}


# Serve frontend static files (for deployment where only one port is exposed)
@app.get("/styles.css")
async def serve_css():
    css_file = FRONTEND_DIR / "styles.css"
    if css_file.exists():
        return FileResponse(str(css_file), media_type="text/css")
    return JSONResponse(content={"error": "File not found"}, status_code=404)

@app.get("/app.js")
async def serve_app_js():
    js_file = FRONTEND_DIR / "app.js"
    if js_file.exists():
        return FileResponse(str(js_file), media_type="application/javascript")
    return JSONResponse(content={"error": "File not found"}, status_code=404)

@app.get("/chat.html")
async def serve_chat():
    """Serve the chat page"""
    chat_file = FRONTEND_DIR / "chat.html"
    if chat_file.exists():
        return FileResponse(str(chat_file))
    return JSONResponse(content={"error": "File not found"}, status_code=404)

@app.get("/test.html")
async def serve_test():
    """Serve the test page"""
    test_file = FRONTEND_DIR / "test.html"
    if test_file.exists():
        return FileResponse(str(test_file))
    return JSONResponse(content={"error": "File not found"}, status_code=404)

@app.get("/index.html")
async def serve_index_html():
    """Serve the main index page explicitly"""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(content={"error": "File not found"}, status_code=404)


_log("all routes defined")
_log("MODULE LOAD COMPLETE")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    _log(f"=== BINDING TO PORT {port} ===")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
