-- ============================================================================
-- SENSAI Feedback Agent — initial multi-user schema
-- ----------------------------------------------------------------------------
-- Backend-mediated model: the FastAPI backend uses the service_role key and is
-- the only writer. RLS is enabled everywhere; the browser only ever reads the
-- `notifications` table directly (Supabase Realtime) authenticated via a Clerk
-- JWT (Clerk configured as a Supabase third-party auth provider). Its `sub`
-- claim is the Clerk user id, matched against notifications.clerk_user_id.
-- ============================================================================

-- Auto-update `updated_at` on row change.
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Fixed value sets kept as enums; extensible sets (role, notification type,
-- training origin) are plain text so new agents/kinds don't need a migration.
do $$ begin
  create type likert_scale as enum (
    'Fortement affaiblie', 'Affaiblie', 'Inchangée', 'Renforcée', 'Fortement renforcée'
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type user_training_status as enum ('not_started', 'in_progress', 'completed');
exception when duplicate_object then null; end $$;

-- ============================================================================
-- users — one row per Clerk user, upserted by the backend on first request.
-- ============================================================================
create table if not exists public.users (
  id            uuid primary key default gen_random_uuid(),
  clerk_user_id text not null unique,
  email         text,
  full_name     text,
  created_at    timestamptz not null default now()
);

-- ============================================================================
-- trainings / situations / scenarios / expert_responses (content catalogue)
-- A "training" = 1+ situations; each situation has ~3 scenarios; each scenario
-- has expert responses (Expert 2..6). Seeded from trainings_2_experts.py.
-- origin: 'seed_mandatory' | 'seed_bank' | 'suggested_bank' | 'generated'
-- ============================================================================
create table if not exists public.trainings (
  id                  uuid primary key default gen_random_uuid(),
  title               text not null,
  domain              text not null default 'migraine',
  origin              text not null default 'seed_bank',
  learning_objectives jsonb not null default '[]'::jsonb,
  created_by          uuid references public.users(id) on delete set null,
  source_training_id  uuid references public.trainings(id) on delete set null,
  created_at          timestamptz not null default now()
);

create table if not exists public.situations (
  id              uuid primary key default gen_random_uuid(),
  training_id     uuid not null references public.trainings(id) on delete cascade,
  situation_index int not null,
  title           text,
  text            text not null,
  created_at      timestamptz not null default now(),
  unique (training_id, situation_index)
);

create table if not exists public.scenarios (
  id              uuid primary key default gen_random_uuid(),
  situation_id    uuid not null references public.situations(id) on delete cascade,
  scenario_index  int not null,
  hypothesis      text not null,          -- "Si vous pensiez ..."
  new_information text not null,          -- "Et qu'alors ..."
  created_at      timestamptz not null default now(),
  unique (situation_id, scenario_index)
);

create table if not exists public.expert_responses (
  id            uuid primary key default gen_random_uuid(),
  scenario_id   uuid not null references public.scenarios(id) on delete cascade,
  expert_label  text not null,            -- "Expert 2" .. "Expert 6"
  likert        likert_scale not null,
  justification text not null,
  created_at    timestamptz not null default now()
);

-- ============================================================================
-- user_trainings — a user's instance/state of a training (dashboard item).
-- ============================================================================
create table if not exists public.user_trainings (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references public.users(id) on delete cascade,
  training_id   uuid not null references public.trainings(id) on delete cascade,
  status        user_training_status not null default 'not_started',
  started_at    timestamptz,
  completed_at  timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (user_id, training_id)
);
create index if not exists user_trainings_user_idx on public.user_trainings(user_id);
create trigger user_trainings_updated_at before update on public.user_trainings
  for each row execute function public.set_updated_at();

-- ============================================================================
-- user_responses — draft-saveable answer per scenario (Likert + justification).
-- ============================================================================
create table if not exists public.user_responses (
  id                uuid primary key default gen_random_uuid(),
  user_training_id  uuid not null references public.user_trainings(id) on delete cascade,
  scenario_id       uuid not null references public.scenarios(id) on delete cascade,
  likert            likert_scale,
  justification     text,
  updated_at        timestamptz not null default now(),
  unique (user_training_id, scenario_id)
);
create index if not exists user_responses_ut_idx on public.user_responses(user_training_id);
create trigger user_responses_updated_at before update on public.user_responses
  for each row execute function public.set_updated_at();

-- ============================================================================
-- evaluations — one per completed user_training (JSON + LLM-generated HTML).
-- ============================================================================
create table if not exists public.evaluations (
  id                uuid primary key default gen_random_uuid(),
  user_training_id  uuid not null unique references public.user_trainings(id) on delete cascade,
  evaluation_json   jsonb not null,
  evaluation_html   text,
  created_at        timestamptz not null default now()
);

-- ============================================================================
-- conversations + messages — one conversation per completed training; every
-- agent message (internal or user-facing) is logged, role-labeled.
-- role: 'user_message' | 'response_message' | 'orchestrator' | 'rag_agent'
--       | 'web_search' | 'evaluator' | 'gap_updater' | 'eval_table'
--       | 'answer_assist' | 'scenario_generator' | 'suggestions' | ...
-- ============================================================================
create table if not exists public.conversations (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references public.users(id) on delete cascade,
  user_training_id  uuid not null unique references public.user_trainings(id) on delete cascade,
  title             text,
  created_at        timestamptz not null default now()
);
create index if not exists conversations_user_idx on public.conversations(user_id);

create table if not exists public.messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role            text not null,
  content         text not null default '',
  metadata        jsonb not null default '{}'::jsonb,  -- tool name, tokens, citations, internal flag, mermaid, ...
  created_at      timestamptz not null default now()
);
create index if not exists messages_conversation_idx on public.messages(conversation_id, created_at);

-- ============================================================================
-- learning_gaps — one evolving structured doc per user.
-- ============================================================================
create table if not exists public.learning_gaps (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null unique references public.users(id) on delete cascade,
  content     text not null default '',      -- structured markdown, grouped by learning objective
  structured  jsonb not null default '{}'::jsonb,
  updated_at  timestamptz not null default now()
);
create trigger learning_gaps_updated_at before update on public.learning_gaps
  for each row execute function public.set_updated_at();

-- ============================================================================
-- notifications — pushed to the browser via Supabase Realtime.
-- clerk_user_id is denormalized so the RLS policy / realtime filter is trivial.
-- type: 'evaluation_ready' | 'feedback_ready' | 'suggestions_ready' | ...
-- ============================================================================
create table if not exists public.notifications (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references public.users(id) on delete cascade,
  clerk_user_id     text not null,
  type              text not null,
  title             text not null,
  body              text,
  user_training_id  uuid references public.user_trainings(id) on delete cascade,
  read              boolean not null default false,
  created_at        timestamptz not null default now()
);
create index if not exists notifications_clerk_idx on public.notifications(clerk_user_id, created_at desc);

-- ============================================================================
-- Row Level Security
-- Backend uses the service_role key, which BYPASSES RLS entirely. We still
-- enable RLS on every table so nothing is exposed by default. The only
-- client-side (anon + Clerk JWT) access is a SELECT on notifications.
-- ============================================================================
alter table public.users            enable row level security;
alter table public.trainings        enable row level security;
alter table public.situations       enable row level security;
alter table public.scenarios        enable row level security;
alter table public.expert_responses enable row level security;
alter table public.user_trainings   enable row level security;
alter table public.user_responses   enable row level security;
alter table public.evaluations      enable row level security;
alter table public.conversations    enable row level security;
alter table public.messages         enable row level security;
alter table public.learning_gaps    enable row level security;
alter table public.notifications    enable row level security;

-- Client may read only its own notifications (Clerk JWT `sub` = clerk_user_id).
drop policy if exists "own notifications readable" on public.notifications;
create policy "own notifications readable"
  on public.notifications for select
  to authenticated
  using ((auth.jwt() ->> 'sub') = clerk_user_id);

-- Realtime publication for the notifications table.
do $$ begin
  alter publication supabase_realtime add table public.notifications;
exception when duplicate_object then null; end $$;
