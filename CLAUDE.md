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

Two content sets ship today, each seeded separately and each with its own response scale
(see *Response scales* below): **migraine** (`trainings_2_experts.py` → `scripts/seed_supabase.py`)
and **gastroenterology** (`data/gastro_trainings.json` → `scripts/seed_gastro.py`).

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
| `backend/likert.py` | The response scales; a training names one via `trainings.likert_scale` |
| `backend/suggestions.py`, `backend/bank_rag.py` | "Suggest new trainings" — query agent → bank vector store → selection agent |
| `models.py`, `prompts.py` (repo root) | Pydantic structured-output schemas + agent prompts |
| `frontend/src/components/AppShell.tsx` | Top bar + left nav (`TABS`) + content switch |
| `frontend/src/components/AppContext.tsx` | Global client state (`Tab` union, conversations, notifications) |
| `frontend/src/components/views/*.tsx` | One component per left-nav tab |
| `frontend/src/lib/api.ts` | `useApi()` — attaches the Clerk token to every backend call |
| `supabase/migrations/*.sql` | Schema. The initial file documents every table inline |
| `scripts/ingest.py` | Offline Chroma indexing (run locally; Cloud Run never indexes) |
| `scripts/seed_supabase.py` | Seeds the **migraine** catalogue from `trainings_2_experts.py` |
| `scripts/parse_training_pdf.py` | Offline: SENSAI export PDF → `data/gastro_trainings.json` (committed) |
| `scripts/seed_gastro.py` | Seeds the **gastro** catalogue from that JSON |

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
   Two inputs are specific to this step: the training's `domain` becomes the agent's
   `training_type` (so a gastro learner is never answered from the migraine PDFs — a
   domain with no `Docs_*` folder degrades to "not covered, try web search"), and the
   situations' `educational_synthesis` is passed as expert grounding. The synthesis is
   deliberately **not** in the interactive chat context.

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
  (`get_training_content(include_experts=True)`). The same goes for
  `situations.educational_synthesis`; both client endpoints run it through
  `app._strip_expert_material`.
- `trainings.origin` = `seed_mandatory` | `seed_bank` | `suggested_bank` | `generated`.
  There are **several** `seed_mandatory` rows (one entry point per theme/domain); every
  learner is assigned all of them at bootstrap and completing **any one** unlocks the
  feedback and suggestions. `list_bank_trainings()` (the suggestion bank) covers only
  `seed_bank`/`suggested_bank`.
- `learning_gaps` — the learner's *current* profile (one row per user, overwritten).
  `learning_gap_history` — append-only snapshot per pipeline run, powering the
  "versions précédentes" view in *Mon apprentissage*.
- `conversations` / `messages` — one conversation per completed training; every agent
  step is logged with a `role`, internal ones filtered out of the client view.
- `notifications` — the one table the browser reads directly (Realtime).

Applying a migration: add a timestamped `.sql` file to `supabase/migrations/`, then
`supabase db push` (needs `SUPABASE_DB_PASSWORD`) or paste it into the Supabase SQL editor.

⚠️ Each seed script **deletes and re-inserts its own domain's** `seed_mandatory`/`seed_bank`
rows, which cascades to any `user_trainings` attached to them. Keep the `domain` scoping in
`_delete_existing_seed` — without it, running one seed wipes the other's content.

## Response scales

Learning by Concordance has more than one valid response scale, and the two content sets
use different ones, so the scale is a property of the training (`trainings.likert_scale`),
not a constant. `backend/likert.py` and `frontend/src/lib/types.ts::LIKERT_SCALES` hold the
two lists and must stay in sync with the `likert_scale` Postgres enum:

| key | values | used by |
|---|---|---|
| `concordance` | Fortement affaiblie … Fortement renforcée | migraine (and the default for older rows) |
| `pertinence` | Pas du tout pertinente … Très pertinente | gastro (which also has *action* scenarios, where "renforcée" would not read) |

Because the permitted values are per-training, `AssistedAnswer.likert` and
`GeneratedExpert.likert` in `models.py` are plain `str`, not `Literal` — the prompt lists
the scale and `likert.coerce()` snaps the answer back onto it.

## Suggestions

`GET /suggestions?preference=…` → `backend/suggestions.py`: a **query agent** turns the
learner's gap profile (plus their optional free-text wish) into a retrieval query, the
`bank_situations` Chroma collection returns candidates, and a **selection agent** picks
1–3 and writes a French rationale. Two rules matter:

- **Per-user exclusion**: trainings already on the learner's dashboard *or* completed are
  filtered out after retrieval. Nothing is removed from the vector store — the bank is
  shared — hence the deliberately wide `top_k`. When everything relevant is already taken,
  the endpoint returns `status: "exhausted"` with a message the UI shows verbatim.
- **Domain fit**: the bank is mixed-domain, so the selection agent is told to keep only
  candidates consistent with the learner's practice area *unless they explicitly asked for
  another subject*. This is prompt-level and stays generic — do not hard-code domain names.

`GET /bank-trainings/{id}` backs the "Voir le contenu" preview on a suggestion card
(objectives + situations + scenarios; never experts or the synthesis).

## Auth

Clerk issues the session JWT; `backend/auth.py` verifies it against Clerk's JWKS and maps
`sub` → a `users` row, creating it (plus the mandatory trainings and an empty profile) on
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
