-- ============================================================================
-- SENSAI Feedback Agent — the "appropriée" Likert scale
-- ----------------------------------------------------------------------------
-- A third body of content (human-computer interaction / IHM, course LOG2420)
-- judges whether a proposed design or process action remains *appropriate* in
-- the light of the new information: "Totalement inappropriée" .. "Totalement
-- appropriée". Neither of the existing scales reads correctly for it —
-- "renforcée" describes a hypothesis's strength and "pertinente" its relevance,
-- while these scenarios ask the learner to judge a decision.
--
-- The five values join the `likert_scale` enum; a training opts in through
-- `trainings.likert_scale = 'appropriee'` (that column is plain text, so no
-- migration is needed for the key itself).
--
-- NOTE: Postgres forbids *using* a newly added enum value in the same
-- transaction that adds it. This migration only adds values; the IHM content is
-- inserted later by scripts/seed_hci.py on a separate connection.
-- ============================================================================

alter type likert_scale add value if not exists 'Totalement inappropriée';
alter type likert_scale add value if not exists 'Inappropriée';
alter type likert_scale add value if not exists 'Ni plus ni moins appropriée';
alter type likert_scale add value if not exists 'Appropriée';
alter type likert_scale add value if not exists 'Totalement appropriée';
