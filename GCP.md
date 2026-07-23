# GCP / Cloud Run — Operations Notes

Everything a future session needs to know about how this project runs on Google Cloud.
For the full deploy walkthrough see [DEPLOYMENT.md](DEPLOYMENT.md); this file is the
GCP-specific quick reference and gotchas.

> ⚠️ Do **not** put real API keys in this file or any committed file. Secrets live in the
> local (gitignored) `.env` and are passed to Cloud Run at deploy time.

## Identity

| Thing | Value |
|---|---|
| GCP project ID | `feedback-chat-agent` |
| Region | `northamerica-northeast1` (Montreal) |
| Cloud Run service | `feedback-chatbot` |
| Backend URL | `https://feedback-chatbot-75563101301.northamerica-northeast1.run.app` |
| Deploy identity | `arman.bakhtiari95@gmail.com` (gcloud auth) |
| Frontend (Vercel) | project `feedback-chat-agent`, `https://feedback-chat-agent.vercel.app` |
| Vector DB | Chroma Cloud, database `feedback-chat` |

## Architecture in one picture

```
Browser ─(direct fetch / CORS)─> Cloud Run (FastAPI)  ─(queries)─> Chroma Cloud
   ▲                                     │
   └── static HTML/JS from Vercel        └── Anthropic + OpenAI + Tavily APIs
```

The Vercel frontend calls Cloud Run **directly** (URL hard-coded as `PROD_BACKEND_URL`
in `frontend/app.js`). It does **not** proxy through Vercel rewrites — `/evaluate` runs
~2 min and would exceed Vercel's gateway timeout. Backend CORS is `allow_origins=["*"]`,
so any frontend origin is accepted.

## How it's built & deployed

- Deployment is **source-based**: `gcloud run deploy --source .` uploads the repo and
  Cloud Build builds the repo-root [Dockerfile](Dockerfile) (python:3.12-slim, installs
  `requirements.txt`, `CMD ["python", "deploy.py"]`). `deploy.py` reads `$PORT` and starts
  uvicorn (`host=0.0.0.0`, `loop=asyncio`, `http=h11`).
- Required GCP APIs (already enabled): `run.googleapis.com`, `cloudbuild.googleapis.com`,
  `artifactregistry.googleapis.com`.
- The built image lives in Artifact Registry (auto-created repo `cloud-run-source-deploy`).
- Upload context respects `.gitignore` (no `.gcloudignore` present), so `.env`, `venv/`,
  `.sessions/` are not uploaded. The `Docs_migraine/` and `Docs_nursing/` PDFs **are**
  shipped (see gotcha below).

### Redeploy command

```bash
gcloud config set project feedback-chat-agent
gcloud run deploy feedback-chatbot \
  --source . \
  --region northamerica-northeast1 \
  --port 8080 --memory 2Gi --cpu 2 \
  --min-instances 1 --max-instances 1 --no-cpu-throttling \
  --timeout 600 --allow-unauthenticated \
  --set-env-vars "^@@^ANTHROPIC_API_KEY=...@@OPENAI_API_KEY=...@@TAVILY_API_KEY=...@@LANGCHAIN_API_KEY=...@@CHROMA_API_KEY=...@@CHROMA_TENANT=...@@CHROMA_DATABASE=feedback-chat"
```

The `^@@^` prefix sets `@@` as the delimiter (values are comma-free but this is safe).
`--set-env-vars` **replaces** all env vars; use `--update-env-vars` to change a subset.

## Runtime configuration (why these flags)

- **`--min-instances 1 --max-instances 1`** — the app keeps sessions as JSON files in
  `.sessions/` and caches `chat_agents` in memory, both per-instance. Pinning to a single
  always-on instance keeps them consistent. Scaling out would require moving sessions to
  GCS/Firestore first.
- **`--no-cpu-throttling`** — CPU stays allocated between requests (background work,
  in-memory cache survive).
- **`--memory 2Gi --cpu 2`** — LangChain + Chroma client + matplotlib footprint.
- **`--timeout 600`** — `/evaluate` takes ~116 s; the default 300 s is enough but 600 is
  headroom.
- **`--allow-unauthenticated`** — public web app; auth is handled (or not) at the app level.

## Environment variables (set on the service)

Required (agents): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `CHROMA_API_KEY`, `CHROMA_TENANT`,
`CHROMA_DATABASE`.
Required (data + auth): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (backend only — bypasses RLS),
`CLERK_ISSUER` (JWKS derived from it, or set `CLERK_JWKS_URL`).
Optional: `SUPABASE_ANON_KEY` (not needed by the backend; the frontend uses it for realtime),
`CORS_ORIGINS` (comma-separated allowlist; defaults to localhost:3000 + the Vercel origin),
`LANGCHAIN_API_KEY` (LangSmith tracing), `TAVILY_API_KEY` (web search; has a fallback).
`PORT` is injected by Cloud Run (8080). See [.env.example](.env.example).

The frontend is a **Next.js app** (Clerk auth) on Vercel; it needs
`NEXT_PUBLIC_API_BASE_URL` (the Cloud Run URL), `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`,
`CLERK_SECRET_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

To move secrets into **Secret Manager** later:
`--set-secrets ANTHROPIC_API_KEY=anthropic-key:latest,...` instead of `--set-env-vars`.

## Chroma Cloud (the vector DB) — not on GCP but essential

- The deployed backend only **queries** Chroma Cloud (read-only). Embeddings are built
  **offline** by `python scripts/ingest.py`, which must be re-run whenever the PDFs in
  `Docs_*` or `bank_situations.py` change. Cloud Run never indexes.
- Collections: `knowledge_base_migraine`, `knowledge_base_nursing`, `bank_situations`.
- Free-tier quotas that bit us (handled in code): IDs ≤128 bytes (chunk IDs are hashed),
  ≤300 records per `collection.add` (adds are batched at 250). Don't undo these.
- `backend/chroma_client.py::get_chroma_client()` picks Chroma Cloud when `CHROMA_API_KEY`
  is set, else a local `.chroma_db` PersistentClient — so local dev needs no cloud account.

## Gotchas for the next session

- **PDFs ship in the image on purpose.** `.dockerignore` keeps `Docs_*` because
  `backend/rag_tool._has_documents()` checks for local PDF presence at runtime to decide
  whether a training type has a knowledge base. Removing them would make the backend report
  "no documents" even though Chroma Cloud has the data. They are ~16 MB and never re-indexed.
- **First request after a cold start / new revision is slow** (heavy lazy imports:
  langchain, chromadb, matplotlib). Keep the lazy imports — they help, not hurt.
- **`chromadb` version:** `requirements.txt` pins `chromadb>=1.5.0`; the old
  `chromadb<1.5.9` note in memory was a *Replit firewall* constraint and no longer applies.
- **Logs / debugging:**
  `gcloud run services logs read feedback-chatbot --region northamerica-northeast1 --limit 100`
  Describe/inspect:
  `gcloud run services describe feedback-chatbot --region northamerica-northeast1`
- **Health check:** `GET /health` → `{"status":"healthy"}`.
- **CORS is wide open** (`allow_origins=["*"]`); if you lock it down, add the Vercel origin
  `https://feedback-chat-agent.vercel.app`.

## Common operations

```bash
# Tail logs
gcloud run services logs read feedback-chatbot --region northamerica-northeast1 --limit 100

# Change one env var without touching the rest
gcloud run services update feedback-chatbot --region northamerica-northeast1 \
  --update-env-vars LANGCHAIN_API_KEY=...

# Roll back to a previous revision
gcloud run services update-traffic feedback-chatbot --region northamerica-northeast1 \
  --to-revisions <REVISION>=100

# Re-ingest the vector DB after changing PDFs / bank (run locally with .env populated)
python scripts/ingest.py
```
