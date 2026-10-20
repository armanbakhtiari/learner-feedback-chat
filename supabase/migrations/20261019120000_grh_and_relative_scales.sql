-- ============================================================================
-- SENSAI Feedback Agent — relative scales, the GRH content, per-scenario format
-- ----------------------------------------------------------------------------
-- 1. The IHM scale becomes *relative*: the learner judges whether the new
--    information makes the proposed decision more or less appropriate
--    ("Beaucoup moins appropriée" .. "Beaucoup plus appropriée"), not how
--    appropriate it is in absolute terms. The middle value already exists.
--    Rows stored on the old wording are remapped by
--    scripts/migrate_ihm_relative_scale.py (ordinal mapping).
-- 2. A fourth body of content (human resources management / GRH) uses two
--    scales inside ONE training:
--      - "raisonnement" scenarios (hypothesis + new information):
--        "Beaucoup moins pertinente" .. "Beaucoup plus pertinente"
--      - "jugement" scenarios (an observed behaviour only, no new information):
--        "Tout à fait inacceptable" .. "Tout à fait acceptable" (4 values)
--    So a scenario can now carry its own format and scale:
--      scenarios.kind         'reasoning' | 'judgment' (plain text, like origin)
--      scenarios.likert_scale null = inherit trainings.likert_scale
--
-- NOTE: Postgres forbids *using* a newly added enum value in the same
-- transaction that adds it. This migration only adds values and columns; data
-- is written later by the seed / migration scripts on separate connections.
-- ============================================================================

alter type likert_scale add value if not exists 'Beaucoup moins appropriée';
alter type likert_scale add value if not exists 'Moins appropriée';
alter type likert_scale add value if not exists 'Plus appropriée';
alter type likert_scale add value if not exists 'Beaucoup plus appropriée';

alter type likert_scale add value if not exists 'Beaucoup moins pertinente';
alter type likert_scale add value if not exists 'Moins pertinente';
alter type likert_scale add value if not exists 'Plus pertinente';
alter type likert_scale add value if not exists 'Beaucoup plus pertinente';

alter type likert_scale add value if not exists 'Tout à fait inacceptable';
alter type likert_scale add value if not exists 'Inacceptable';
alter type likert_scale add value if not exists 'Acceptable';
alter type likert_scale add value if not exists 'Tout à fait acceptable';

-- How the scenario is posed: 'reasoning' = "Si vous pensiez à… / Et qu'alors…",
-- 'judgment' = a single observed behaviour to judge (new_information is '').
alter table public.scenarios
  add column if not exists kind text not null default 'reasoning';

-- Per-scenario override of trainings.likert_scale; null means "use the training's".
alter table public.scenarios
  add column if not exists likert_scale text;
