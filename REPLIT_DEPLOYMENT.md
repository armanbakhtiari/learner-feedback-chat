# Replit Deployment Guide

## How the Deployment Works

The app is deployed on Replit Autoscale using Google Cloud Run under the hood. The FastAPI backend serves both the API and the frontend static files on a single port.

**Live URL:** `https://learner-feedback-chat--armanbakhtiari9.replit.app`

## The Health Check Problem (Solved)

Replit Autoscale deployments kept failing with:

> The deployment is failing health checks.

### Root Cause

Three issues were blocking deployment:

1. **No build step** - Packages from `requirements.txt` weren't installed during deployment. Fixed by adding `build = ["pip", "install", "-r", "requirements.txt"]` to `[deployment]`.

2. **Missing `deploymentTarget`** - Without `deploymentTarget = "cloudrun"`, Replit's Autoscale service didn't properly route health check traffic to the container.

3. **Wrong port** - The `[[ports]]` section and metasidecar were intercepting traffic. The metasidecar's port forwarding only handled browser traffic, NOT health checks from the Autoscale infrastructure. The fix was to remove `[[ports]]` entirely and use `PORT = "8080"` (Cloud Run's default port).

### What Didn't Work

- Binding to port 8000 with `[[ports]]` forwarding (8000 -> 80) - health checks never reached the app
- Binding directly to port 80 - metasidecar still intercepted
- Using `deploymentTarget` without removing `[[ports]]` - conflict between metasidecar and direct routing

### What Worked

The final `.replit` configuration:

```toml
run = "python3 run.py"

[nix]
channel = "stable-25_05"
packages = ["cairo", "ffmpeg-full", "freetype", "ghostscript", "glibcLocales", "gobject-introspection", "gtk3", "gumbo", "harfbuzz", "jbig2dec", "libjpeg_turbo", "libxcrypt", "mupdf", "openjpeg", "pkg-config", "python312Packages.pip", "qhull", "swig", "tcl", "tk", "xcbuild"]

[deployment]
build = ["sh", "-c", "python3 -m venv --without-pip /home/runner/workspace/.venv && curl -sS https://bootstrap.pypa.io/get-pip.py | /home/runner/workspace/.venv/bin/python3 && /home/runner/workspace/.venv/bin/pip install -r requirements.txt"]
run = ["/home/runner/workspace/.venv/bin/python3", "backend/app.py"]
deploymentTarget = "cloudrun"

[env]
REPL_DEPLOYMENT = "true"
PYTHONUNBUFFERED = "1"
PORT = "8080"
```

Key points:
- **No `[[ports]]` section** - prevents metasidecar interference
- **`deploymentTarget = "cloudrun"`** - tells Replit to use Cloud Run routing
- **`PORT = "8080"`** - Cloud Run's default health check port; the app reads this via `os.environ.get("PORT", 8000)`
- **Build uses a venv** - Replit's nix-managed Python (PEP 668) blocks direct pip installs. The build step creates a virtual environment with `--without-pip` (to skip the blocked `ensurepip`), bootstraps pip via `get-pip.py`, then installs requirements into the venv. The run command uses the venv's Python.
- **No `.replit.toml`** - having this file can cause conflicting port configurations

## Architecture

```
[Replit Cloud Run] --health check--> :8080 --> FastAPI app
                   --user traffic---> :8080 --> FastAPI app
                                                  |
                                                  |--> /          -> index.html (frontend)
                                                  |--> /health    -> {"status": "healthy"}
                                                  |--> /trainings -> training data API
                                                  |--> /evaluate  -> run evaluations API
                                                  |--> /chat      -> chat agent API
                                                  |--> /*.html    -> static frontend files
                                                  |--> /*.css/js  -> static assets
```

## Local Development

Locally, `python3 run.py` starts:
- Backend on port 8000 (via `backend/app.py`)
- Frontend on port 3000 (via `python -m http.server`)

The `PORT` env var isn't set locally, so the app defaults to port 8000.

## Replit Secrets

Configure these in Replit's Secrets tab (not `.env`):
- `ANTHROPIC_API_KEY` - for Claude (chat agent)
- `OPENAI_API_KEY` - for embeddings (RAG)
- `LANGCHAIN_API_KEY` - for LangSmith tracing
- `TAVILY_API_KEY` - for web search
