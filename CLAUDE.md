# CLAUDE.md

Orientation for a new session working on this repo. Ops details live in
[GCP.md](GCP.md) (Cloud Run specifics + gotchas) and [DEPLOYMENT.md](DEPLOYMENT.md)
(step-by-step deploy); this file is the map.

## What this is

**SENSAI Feedback Agent** — a multi-user French-language *Learning by Concordance* (LbC)
training app. A learner answers scenarios (Likert + written justification), the answers
are evaluated against a panel of experts, and an LLM agent gives non-judgmental feedback
while maintaining an evolving profile of the learner's gaps.

**LbC principle that constrains the whole product: no scores, no pass/fail, no red/green
semaphores.** Everything user-facing is qualitative and in French. Keep it that way.

## Architecture

```
Browser ──> Vercel (Next.js 15, Clerk auth)
   │
   │ direct fetch + CORS, Clerk session JWT as Bearer token
   │ (NOT proxied through Vercel — /evaluate runs ~2 min, over the gateway timeout)
   ▼
Cloud Run (FastAPI, single pinned instance) ──> Supabase Postgres (service_role)
   │                                        └─> Chroma Cloud (RAG) + Anthropic/OpenAI/Tavily
   ▼
Browser also opens a direct Supabase Realtime channel (Clerk JWT) to read `notifications`.
```

**Backend-mediated data model:** the backend holds the `service_role` key and is the
*only* writer to Supabase. RLS is on for every table; the sole client-side policy lets a
user `SELECT` their own `notifications` (matched on the Clerk `sub` claim). Never add
browser-side writes — route them through a FastAPI endpoint.

## Key files

| Path | Role |
|---|---|
| `backend/app.py` | All HTTP endpoints; every one takes `Depends(get_current_user)` |
| `backend/auth.py` | Clerk JWT verification (JWKS/RS256) → Supabase `users` row; email fallback |
| `backend/db/repo.py` | Every Supabase read/write. Add DB access here, not in endpoints |
| `backend/pipeline.py` | Post-evaluation pipeline (the heart of the app — see below) |
| `backend/evaluator.py` | LLM → structured `TrainingEvaluation` (schema in root `models.py`) |
| `backend/eval_table_agent.py` | Deterministic (no LLM) builder for the completed-tab table |
| `backend/gap_updater.py` | LLM that merges an evaluation into the learner's profile |
| `backend/chat_agent.py` | LangGraph feedback agent (RAG + web search tools) |
| `backend/rag_tool.py`, `backend/chroma_client.py` | Chroma Cloud retrieval (heavy, lazy-imported) |
| `models.py`, `prompts.py` (repo root) | Pydantic structured-output schemas + agent prompts |
| `frontend/src/components/AppShell.tsx` | Top bar + left nav (`TABS`) + content switch |
| `frontend/src/components/AppContext.tsx` | Global client state (`Tab` union, conversations, notifications) |
| `frontend/src/components/views/*.tsx` | One component per left-nav tab |
| `frontend/src/lib/api.ts` | `useApi()` — attaches the Clerk token to every backend call |
| `supabase/migrations/*.sql` | Schema. The initial file documents every table inline |
| `scripts/ingest.py` | Offline Chroma indexing (run locally; Cloud Run never indexes) |
| `scripts/seed_supabase.py` | Seeds the training catalogue from `trainings_2_experts.py` |

## The completion pipeline

`POST /trainings/{id}/evaluate` → `backend/pipeline.py::run_completion_pipeline`, which
runs **synchronously** (`await asyncio.to_thread`, ~2 min) because Cloud Run freezes
background work once a response is sent. Steps, each logged to the training's conversation
and best-effort (a failing step never kills the run):

1. **Evaluator** — `training_parser.build_evaluation_input` rebuilds the marker-delimited
   text from DB content + the learner's answers → structured `evaluation_json`.
2. **Eval table** — `build_eval_table` zips `evaluation_json` with the training content to
   produce a scenario-linked table → `evaluations.eval_table_json`. → notify.
3. **Gap updater** — merges the evaluation into the learner's profile; writes the current
   version to `learning_gaps` **and** appends a snapshot to `learning_gap_history`.
4. **Initial feedback** — creates the conversation's first agent message. → notify.

⚠️ **The evaluator's `"situation N"` / `"scenario M"` keys are positional**, matching the
order `build_evaluation_input` walked (situations by `situation_index`, scenarios by
`scenario_index` — the same order `repo.get_training_content()` returns). `build_eval_table`
relies on this to recover real `scenario_id`s without an LLM. If you change either
ordering, change both.

## Database

Schema and inline commentary: `supabase/migrations/`. Shape:

- `users` (one per Clerk user) → `user_trainings` (a user's instance of a training) →
  `user_responses` (per scenario) → `evaluations` (one per completed user_training).
- Content catalogue: `trainings` → `situations` → `scenarios` → `expert_responses`.
  **Expert responses must never reach a client path** — only the evaluator reads them
  (`get_training_content(include_experts=True)`).
- `learning_gaps` — the learner's *current* profile (one row per user, overwritten).
  `learning_gap_history` — append-only snapshot per pipeline run, powering the
  "versions précédentes" view in *Mon apprentissage*.
- `conversations` / `messages` — one conversation per completed training; every agent
  step is logged with a `role`, internal ones filtered out of the client view.
- `notifications` — the one table the browser reads directly (Realtime).

Applying a migration: add a timestamped `.sql` file to `supabase/migrations/`, then
`supabase db push` (needs `SUPABASE_DB_PASSWORD`) or paste it into the Supabase SQL editor.

## Auth

Clerk issues the session JWT; `backend/auth.py` verifies it against Clerk's JWKS and maps
`sub` → a `users` row, creating it (plus the mandatory training and an empty profile) on
first sign-in. **Clerk's default session token has no `email` claim**, so `auth.py` falls
back to the Clerk Backend API (`CLERK_SECRET_KEY`) to resolve it, caching successes and
backfilling rows whose email is still null. Adding `{"email": "{{user.primary_email_address}}"}`
under Clerk → Sessions → customize session token avoids that extra call.
`scripts/backfill_user_emails.py` fixes users who never sign in again.

## Local development

```bash
pip install -r requirements.txt          # backend
cp .env.example .env                     # then fill it in
uvicorn backend.app:app --reload --port 8000

cd frontend && npm install && npm run dev  # http://localhost:3000
```

Frontend needs `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` plus the Clerk/Supabase
`NEXT_PUBLIC_*` vars in `frontend/.env.local`. With `CHROMA_API_KEY` unset the backend
uses a local `.chroma_db` (run `python scripts/ingest.py` once to populate it).

> `run.py` is the **legacy** single-user launcher (it serves the old static frontend) —
> it does not run the Next.js app. Use the two commands above.

Before pushing: `cd frontend && npm run build` (there is no CI to catch breakage).

## Deploying

Manual, no CI/CD. Migration first, then:

```bash
gcloud run deploy feedback-chatbot --source . --region northamerica-northeast1 ...  # see GCP.md
cd frontend && vercel deploy --prod
```

Full flags, env vars, and the reasoning behind the single-instance pinning: [GCP.md](GCP.md).

## Conventions

- French for everything user-facing (UI copy, agent output, notifications); English for
  code, comments, and prompts.
- Frontend styling is hand-written Tailwind — no component library. Match the existing
  vocabulary (`rounded-xl border border-slate-200 bg-white shadow-sm` cards, `bg-brand`
  for primary actions) and add SVGs to `frontend/src/components/Icons.tsx` rather than
  pulling in an icon package.
- Heavy backend imports (langchain, chromadb) stay lazy/function-local to protect cold starts.
- `credentials.md` is gitignored and holds live secrets — never read it into a commit,
  a doc, or a message.
