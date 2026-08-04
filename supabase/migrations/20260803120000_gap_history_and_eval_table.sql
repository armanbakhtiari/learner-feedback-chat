-- ============================================================================
-- SENSAI Feedback Agent — learner-profile history + structured evaluation table
-- ----------------------------------------------------------------------------
-- 1. learning_gap_history: append-only snapshot of the learner's profile, one
--    row per completion-pipeline run. `learning_gaps` keeps holding the CURRENT
--    profile (unchanged contract for the chat/suggestions agents); this table is
--    what the "Mon apprentissage" tab reads to show previous versions by date.
-- 2. evaluations.eval_table_json: the evaluation table is now built
--    deterministically in Python (backend/eval_table_agent.py) instead of being
--    generated as freeform HTML by an LLM, so each row can carry its real
--    scenario id and the learner's own answer. `evaluation_html` is left in
--    place (no longer written) so the migration stays non-destructive.
-- ============================================================================

create table if not exists public.learning_gap_history (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.users(id) on delete cascade,
  content     text not null default '',      -- markdown profile as of this update
  structured  jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists learning_gap_history_user_idx
  on public.learning_gap_history(user_id, created_at desc);

-- Backend (service_role) is the only reader/writer; RLS on by default like everywhere else.
alter table public.learning_gap_history enable row level security;

alter table public.evaluations add column if not exists eval_table_json jsonb;
