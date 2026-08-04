# Deployment

Backend → **Google Cloud Run** (Docker). Frontend → **Vercel** (Next.js).
Data → **Supabase** (Postgres). Auth → **Clerk**. Vector DB → **Chroma Cloud**.
The deployed backend only *queries* Chroma; embeddings are built offline by
`scripts/ingest.py`.

## Architecture

```
Browser ──> Vercel (Next.js app, Clerk auth)
   │
   │ direct fetch (CORS) to NEXT_PUBLIC_API_BASE_URL, Clerk session JWT as Bearer token
   ▼
Cloud Run (FastAPI backend, single instance)
   │ service_role writes            │ queries
   ▼                                ▼
Supabase Postgres            Chroma Cloud (knowledge_base_*, bank_situations)
```

> **Why direct CORS instead of Vercel rewrites?** `/evaluate` runs for ~2 minutes
> (many LLM calls), which exceeds Vercel's gateway timeout for proxied requests. So the
> browser calls Cloud Run directly, using the URL in `NEXT_PUBLIC_API_BASE_URL`.
> No `vercel.json` rewrites are used.

## Environment variables

See [.env.example](.env.example). Backend required: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
the Chroma trio `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE`, `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, `CLERK_ISSUER`, and `CLERK_SECRET_KEY` (used to resolve a new
user's email — see [CLAUDE.md](CLAUDE.md#auth)).
Optional: `LANGCHAIN_API_KEY`, `TAVILY_API_KEY`, `CORS_ORIGINS`.

Frontend (Vercel project settings): `NEXT_PUBLIC_API_BASE_URL`,
`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY`.

When `CHROMA_API_KEY` is unset the app falls back to a local `.chroma_db` store, so local
dev needs no Chroma Cloud account.

## 0. Apply pending database migrations (before deploying the backend)

```bash
supabase db push     # needs SUPABASE_DB_PASSWORD; or paste the .sql into the Supabase SQL editor
```

Migrations live in `supabase/migrations/` and are **not** applied by the Cloud Run deploy.
Push the schema first — a new backend revision expects the new columns/tables.

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
  --set-env-vars CHROMA_API_KEY=...,CHROMA_TENANT=...,CHROMA_DATABASE=...,ANTHROPIC_API_KEY=...,OPENAI_API_KEY=...,TAVILY_API_KEY=...,LANGCHAIN_API_KEY=...,SUPABASE_URL=...,SUPABASE_SERVICE_ROLE_KEY=...,CLERK_ISSUER=...,CLERK_SECRET_KEY=...
```

`--source .` builds the [Dockerfile](Dockerfile). `--min/max-instances 1` +
`--no-cpu-throttling` pin the app to a single always-on instance, which keeps the
file-based session store (`.sessions/`) and the in-memory `chat_agents` cache consistent.
Prefer Secret Manager over `--set-env-vars` for secrets:
`--set-secrets ANTHROPIC_API_KEY=anthropic-key:latest,...`.

Note the service URL it prints (e.g. `https://feedback-chatbot-xxxx.run.app`).

Smoke test: `curl https://<SERVICE_URL>/health` → `{"status":"healthy"}`.

## 3. Deploy the frontend to Vercel

1. Set `NEXT_PUBLIC_API_BASE_URL` on the Vercel project to the full Cloud Run service URL
   (with `https://`, no trailing slash), alongside the Clerk/Supabase vars listed above.
   Update them with `vercel env` or in the project dashboard.
2. Deploy the **`frontend/`** directory as the project root:
   ```bash
   cd frontend && vercel deploy --prod --yes --scope <your-scope>
   ```
   Or connect the GitHub repo with **Root Directory = `frontend`**. `frontend/vercel.json`
   pins `"framework": "nextjs"` — the project predates the Next.js rewrite and its stale
   preset 404s every route without it. Don't remove it.
3. **Disable Deployment Protection** so the site is public. New Vercel projects enable
   "Vercel Authentication" by default, which gates the whole site behind SSO login. Turn
   it off in Project → Settings → Deployment Protection (or via the API:
   `PATCH https://api.vercel.com/v9/projects/<projectId>?teamId=<teamId>` with
   `{"ssoProtection": null}`).

The browser fetches the Cloud Run URL directly (CORS); nothing is proxied through Vercel.

## Local development

```bash
uvicorn backend.app:app --reload --port 8000     # backend
cd frontend && npm run dev                        # frontend on :3000
```

With no `CHROMA_API_KEY` set the backend uses the local `.chroma_db`; run
`python scripts/ingest.py` once to populate it. The frontend reads its config from
`frontend/.env.local` (same `NEXT_PUBLIC_*` vars as Vercel, pointing at `localhost:8000`).

> `run.py` is the legacy single-user launcher for the old static frontend; it does not
> start the Next.js app.

## Security

Rotate any API keys that were previously committed to `.env`
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGCHAIN_API_KEY`).
`.env` is git-ignored and excluded from the Docker image via [.dockerignore](.dockerignore).
