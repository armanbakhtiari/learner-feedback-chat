# Deployment

Backend → **Google Cloud Run** (Docker). Frontend → **Vercel** (static).
Vector DB → **Chroma Cloud** (persistent). The deployed backend only *queries* Chroma;
embeddings are built offline by `scripts/ingest.py`.

## Architecture

```
Browser ──> Vercel (static frontend only: HTML/CSS/JS)
   │
   │ direct fetch (CORS) to the Cloud Run URL in frontend/app.js (PROD_BACKEND_URL)
   ▼
Cloud Run (FastAPI backend, single instance)
   │ queries
   ▼
Chroma Cloud (knowledge_base_*, bank_situations)
```

> **Why direct CORS instead of Vercel rewrites?** `/evaluate` runs for ~2 minutes
> (many LLM calls), which exceeds Vercel's gateway timeout for proxied requests. So the
> browser calls Cloud Run directly. The backend already sets permissive CORS
> (`allow_origins=["*"]`), and `frontend/app.js` holds the Cloud Run URL in
> `PROD_BACKEND_URL`. No `vercel.json` rewrites are used.

## Environment variables

See [.env.example](.env.example). Required: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and
the Chroma Cloud trio `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE`.
Optional: `LANGCHAIN_API_KEY`, `TAVILY_API_KEY`.

When `CHROMA_API_KEY` is unset the app falls back to a local `.chroma_db` store, so local
dev needs no Chroma Cloud account.

## 1. Ingest documents into Chroma Cloud (run once, locally)

Populate the vector store before the first deploy and re-run whenever the PDFs in
`Docs_migraine/` / `Docs_nursing/` or `bank_situations.py` change.

```bash
pip install -r requirements.txt
# .env must contain OPENAI_API_KEY + the CHROMA_* trio
python scripts/ingest.py
```

It builds `knowledge_base_migraine`, `knowledge_base_nursing`, and `bank_situations`,
then prints chunk counts. Verify the collections in the Chroma Cloud dashboard.

## 2. Deploy the backend to Cloud Run

```bash
gcloud run deploy feedback-chatbot \
  --source . \
  --region <REGION> \
  --port 8080 \
  --memory 2Gi \
  --min-instances 1 --max-instances 1 \
  --no-cpu-throttling \
  --allow-unauthenticated \
  --set-env-vars CHROMA_API_KEY=...,CHROMA_TENANT=...,CHROMA_DATABASE=...,ANTHROPIC_API_KEY=...,OPENAI_API_KEY=...,TAVILY_API_KEY=...,LANGCHAIN_API_KEY=...
```

`--source .` builds the [Dockerfile](Dockerfile). `--min/max-instances 1` +
`--no-cpu-throttling` pin the app to a single always-on instance, which keeps the
file-based session store (`.sessions/`) and the in-memory `chat_agents` cache consistent.
Prefer Secret Manager over `--set-env-vars` for secrets:
`--set-secrets ANTHROPIC_API_KEY=anthropic-key:latest,...`.

Note the service URL it prints (e.g. `https://feedback-chatbot-xxxx.run.app`).

Smoke test: `curl https://<SERVICE_URL>/health` → `{"status":"ok"}`.

## 3. Deploy the frontend to Vercel

1. Set the backend URL in [frontend/app.js](frontend/app.js): `PROD_BACKEND_URL` must be
   the full Cloud Run service URL (with `https://`, no trailing slash).
2. Deploy the **`frontend/`** directory as the project root (plain static files, no build):
   ```bash
   cd frontend && vercel deploy --prod --yes --scope <your-scope>
   ```
   Or connect the GitHub repo with **Root Directory = `frontend`**, framework **Other**.
3. **Disable Deployment Protection** so the site is public. New Vercel projects enable
   "Vercel Authentication" by default, which gates the whole site behind SSO login. Turn
   it off in Project → Settings → Deployment Protection (or via the API:
   `PATCH https://api.vercel.com/v9/projects/<projectId>?teamId=<teamId>` with
   `{"ssoProtection": null}`).

The browser fetches the Cloud Run URL directly (CORS); nothing is proxied through Vercel.

## Local development (unchanged)

`python run.py` serves the backend on `:8000` and the static frontend on `:3000`.
With no `CHROMA_API_KEY` set it uses the local `.chroma_db`; run `python scripts/ingest.py`
once to populate it.

## Security

Rotate any API keys that were previously committed to `.env`
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGCHAIN_API_KEY`).
`.env` is git-ignored and excluded from the Docker image via [.dockerignore](.dockerignore).
