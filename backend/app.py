print("🔄 Starting app.py import...", flush=True)
import sys
print("✓ sys imported", flush=True)

from fastapi import FastAPI, HTTPException
print("✓ FastAPI imported", flush=True)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path
print("✓ Standard imports done", flush=True)

from dotenv import load_dotenv
from contextlib import asynccontextmanager
print("✓ All imports done", flush=True)

load_dotenv()
print("✓ dotenv loaded", flush=True)

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Feedback_Chat_Agent"
if not os.getenv("LANGCHAIN_API_KEY"):
    print("⚠️  Warning: LANGCHAIN_API_KEY not found in .env file. LangSmith tracing will be disabled.")

sys.path.append(str(Path(__file__).parent.parent))

# Lazy imports - only import heavy modules when needed
_training_data = None
_evaluator_module = None
_chat_agent_class = None


def get_training_data():
    """Lazy load training data"""
    global _training_data
    if _training_data is None:
        from trainings_2_experts import training_1, training_2, training_3, training_objectives
        _training_data = (training_1, training_2, training_3, training_objectives)
    return _training_data


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Log that the app is ready
    print("🚀 Application lifespan starting...", flush=True)
    print(f"📁 Frontend directory: {FRONTEND_DIR}", flush=True)
    print(f"📁 Frontend exists: {FRONTEND_DIR.exists()}", flush=True)
    print("✅ Health check endpoint ready at /health and /", flush=True)
    print("✅ Application ready to receive requests", flush=True)
    yield
    # Shutdown
    print("👋 Application shutting down...", flush=True)


print("✓ Creating FastAPI app...", flush=True)
app = FastAPI(title="Learner Feedback Chat System", lifespan=lifespan)
print("✓ FastAPI app created", flush=True)

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
print(f"✓ Paths configured: ROOT={ROOT_DIR}, FRONTEND={FRONTEND_DIR}", flush=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store evaluations in memory (in production, use a database)
evaluations_store: Dict[str, Any] = {}
chat_agents: Dict[str, Any] = {}  # Type is Any to avoid importing ChatAgent at module level


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


# API Routes (must come before static file serving)


@app.get("/trainings")
async def get_trainings():
    """Get all training modules"""
    t1, t2, t3, objectives = get_training_data()
    trainings = [
        {
            "id": "training_1",
            "name": "Module 1: Diagnostic et suivi de la migraine",
            "content": t1,
            "objectives": objectives
        },
        {
            "id": "training_2",
            "name": "Module 2: Traitement aigu et gestion des habitudes de vie de la migraine",
            "content": t2,
            "objectives": objectives
        },
        {
            "id": "training_3",
            "name": "Module 3: Traitement préventif de la migraine",
            "content": t3,
            "objectives": objectives
        }
    ]
    return {"trainings": trainings}


@app.post("/evaluate")
async def evaluate_trainings():
    """Run evaluations on all training modules"""
    try:
        run_evaluations = get_evaluator()
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
            ChatAgent = get_chat_agent_class()
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


@app.get("/health")
async def health_check():
    """Health check endpoint - must be very fast"""
    return JSONResponse(content={"status": "ok"}, status_code=200)


# Root endpoint - MUST respond immediately for health checks
@app.get("/")
async def root():
    """Root endpoint - serves frontend or health check response"""
    # Check if this is a health check (no Accept header for HTML)
    # For deployment health checks, return JSON quickly
    if FRONTEND_DIR.exists():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
    # Fallback to JSON response (for health checks or if frontend missing)
    return JSONResponse(content={"status": "ok", "message": "Learner Feedback Chat System"}, status_code=200)


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


print("✅ All routes registered, app.py import complete!", flush=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
