-- ============================================================================
-- SENSAI Feedback Agent — per-training Likert scale + educational synthesis
-- ----------------------------------------------------------------------------
-- 1. A second body of content (gastroenterology) uses a *pertinence* Likert
--    scale ("Pas du tout pertinente" .. "Très pertinente") rather than the
--    *concordance-strength* scale the migraine content uses ("Fortement
--    affaiblie" .. "Fortement renforcée"). Both are valid Learning-by-
--    Concordance response scales, and several gastro scenarios are ACTION
--    scenarios ("Administrer des fluides ...") where "pertinente" reads
--    correctly and "renforcée" does not — so the scale becomes a property of
--    the training instead of a global constant. The `likert_scale` enum gains
--    the five new values; `trainings.likert_scale` names which set a training
--    uses ('concordance' | 'pertinence'), defaulting to the existing behaviour.
-- 2. situations.educational_synthesis: the "Synthèse éducative" shipped with
--    each gastro situation (messages clés des experts + compléments
--    d'apprentissage). It is expert reference material, so like
--    expert_responses it must NEVER reach a client path — it is read only by
--    the completion pipeline, which feeds it to the feedback agent when it
--    writes the initial feedback.
--
-- NOTE: Postgres forbids *using* a newly added enum value in the same
-- transaction that adds it. This migration only adds values and columns; the
-- gastro content is inserted later by scripts/seed_gastro.py on a separate
-- connection, so this is safe to run as one migration.
-- ============================================================================

alter type likert_scale add value if not exists 'Pas du tout pertinente';
alter type likert_scale add value if not exists 'Peu pertinente';
alter type likert_scale add value if not exists 'Ni plus ni moins pertinente';
alter type likert_scale add value if not exists 'Pertinente';
alter type likert_scale add value if not exists 'Très pertinente';

-- Which response scale this training's scenarios use. Kept as text (not an
-- enum) so adding a third scale never needs a migration — same reasoning as
-- `origin` and the message `role` column in the initial schema.
alter table public.trainings
  add column if not exists likert_scale text not null default 'concordance';

-- Expert reference material for a situation. Backend-only, like expert_responses.
alter table public.situations
  add column if not exists educational_synthesis text;
