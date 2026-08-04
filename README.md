# SENSAI — Feedback Agent

A multi-user, French-language **Learning by Concordance** (LbC) training platform. Learners
answer clinical scenarios (Likert rating + written justification); their reasoning is
evaluated against a panel of experts, and an LLM agent delivers non-judgmental feedback
while maintaining an evolving profile of the learner's gaps.

> **LbC principle:** no numeric scores, no pass/fail, no red/green semaphores. All
> user-facing output is qualitative and in French.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router) + Tailwind, deployed on Vercel |
| Auth | Clerk (session JWT verified backend-side against JWKS) |
| Backend | FastAPI on Google Cloud Run |
| Database | Supabase Postgres (backend-mediated: `service_role`, RLS on everywhere) |
| Agents | LangGraph + LangChain, Claude Sonnet |
| Retrieval | Chroma Cloud (indexed offline) + Tavily web search |
| Observability | LangSmith (optional) |

## Quick start

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env                       # fill in the keys
uvicorn backend.app:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev  # http://localhost:3000
```

`frontend/.env.local` needs `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` plus the
Clerk and Supabase `NEXT_PUBLIC_*` keys. With `CHROMA_API_KEY` unset the backend uses a
local `.chroma_db` — run `python scripts/ingest.py` once to populate it, and
`python scripts/seed_supabase.py` to seed the training catalogue.

## How it works

1. A learner is assigned the mandatory training on first sign-in and answers each
   scenario (Likert + justification), with an optional AI answer-assist.
2. `POST /trainings/{id}/evaluate` runs the completion pipeline (~2 min, synchronous):
   evaluate against the expert panel → build the evaluation table → update the learner's
   gap profile → generate the first feedback message. Progress arrives as Supabase
   Realtime notifications.
3. The learner reviews the evaluation table per scenario (drilling into the original
   scenario and their own answer), chats with the feedback agent, sees their profile and
   its previous versions, and picks or generates follow-up trainings targeting their gaps.

## Application tabs

| Tab | What it shows |
|---|---|
| Tableau de bord | Assigned trainings not yet completed |
| Complétées | Completed trainings + the per-scenario evaluation table |
| Suggestions | Bank trainings matched to the learner's gaps, or newly generated ones |
| Agent de rétroaction | Feedback conversations, one per completed training |
| Mon apprentissage | Current gap profile + previous versions by date |
| Notifications | Pipeline milestones |

## API

All endpoints require a Clerk bearer token and are scoped to the authenticated user.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/me` | Current user; bootstraps on first call |
| GET | `/dashboard` | Assigned, not-yet-completed trainings |
| GET | `/completed` | Completed trainings + structured evaluation tables |
| GET | `/trainings/{id}` | Full training content + the learner's saved answers |
| PUT | `/trainings/{id}/responses` | Save answers (draftable) |
| POST | `/trainings/{id}/assist` | AI-suggested answer for one scenario |
| POST | `/trainings/{id}/evaluate` | Run the completion pipeline |
| GET | `/conversations` | Feedback conversations |
| GET | `/conversations/{id}/messages` | Messages in a conversation |
| POST | `/conversations/{id}/chat` | Chat with the feedback agent |
| GET | `/learning-gaps` | Current learner profile |
| GET | `/learning-gaps/history` | Previous profile versions, newest first |
| GET | `/notifications`, POST `/notifications/{id}/read` | Notifications |
| GET | `/suggestions`, POST `/suggestions/pick`, POST `/suggestions/generate` | Suggested trainings |

## Project structure

```
backend/
  app.py               FastAPI endpoints
  auth.py              Clerk JWT verification → Supabase user
  db/repo.py           All Supabase access
  pipeline.py          Post-evaluation pipeline
  evaluator.py         Expert-concordance evaluation (LLM)
  eval_table_agent.py  Deterministic evaluation-table builder
  gap_updater.py       Evolving learner-gap profile (LLM)
  chat_agent.py        LangGraph feedback agent
  rag_tool.py          Chroma retrieval (lazy-imported)
frontend/src/
  components/          AppShell (nav), AppContext (state), views/ (one per tab)
  lib/                 api client, Supabase client, shared types
supabase/migrations/   Schema (documented inline)
scripts/               ingest.py, seed_supabase.py, backfill_user_emails.py
models.py, prompts.py  Structured-output schemas + agent prompts
```

## Documentation

- [CLAUDE.md](CLAUDE.md) — architecture, key files, conventions (start here)
- [GCP.md](GCP.md) — Cloud Run operations, env vars, gotchas
- [DEPLOYMENT.md](DEPLOYMENT.md) — step-by-step deployment
