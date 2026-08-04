"""
Post-evaluation completion pipeline (runs in the background after /evaluate).

Steps (each logged role-labeled to the training's conversation; notifications pushed
via Supabase Realtime as milestones complete):
  1. Evaluator      — build evaluator input from DB content + the learner's typed answers,
                      produce the structured evaluation JSON.
  2. Eval-table     — deterministic build of the scenario-linked evaluation table.
                      → notify evaluation_ready
  3. Gap updater    — merge the evaluation into the learner's evolving learning-gap profile.
  4. Initial feedback — create the conversation and generate the first (Markdown) feedback.
                      → notify feedback_ready
"""

from typing import Any, Dict, List

from backend.db import repo
from backend import message_logger as mlog
from backend.training_parser import build_evaluation_input
from backend.evaluator import evaluate_training
from backend.eval_table_agent import build_eval_table
from backend.gap_updater import update_learning_gap
from backend.chat_agent import ChatAgent


def _objectives_list(training: Dict[str, Any]) -> List[str]:
    objs = training.get("learning_objectives") or []
    return objs if isinstance(objs, list) else [str(objs)]


def run_completion_pipeline(user: Dict[str, Any], user_training_id: str) -> None:
    """Full pipeline for one completed training. Best-effort per step; never raises."""
    try:
        ut = repo.get_user_training(user_training_id)
        if not ut:
            return
        training = repo.get_training_content(ut["training_id"], include_experts=True)
        objectives = _objectives_list(training)
        objectives_str = "\n".join(f"- {o}" for o in objectives)
        situations = training.get("situations", [])
        responses = {r["scenario_id"]: r for r in repo.get_responses(user_training_id)}

        # Conversation is created up front so every pipeline step can be logged to it.
        conversation = repo.create_conversation(user["id"], user_training_id, training["title"])
        conv_id = conversation["id"]

        # 1) Evaluate ---------------------------------------------------------
        content = build_evaluation_input(training["title"], objectives, situations, responses)
        evaluation_json = evaluate_training(content, training["title"])
        repo.save_evaluation(user_training_id, evaluation_json)
        mlog.log_message(conv_id, mlog.ROLE_EVALUATOR, "Évaluation structurée générée.",
                         internal=True, metadata={"evaluation": evaluation_json})

        # 2) Evaluation table (structured, scenario-linked) -------------------
        try:
            table = build_eval_table(evaluation_json, training, responses)
            repo.update_eval_table(user_training_id, table)
            mlog.log_message(conv_id, mlog.ROLE_EVAL_TABLE, "Tableau d'évaluation généré.", internal=True)
        except Exception as e:
            print(f"⚠️  eval-table failed: {e}")
        repo.add_notification(user, "evaluation_ready", "Évaluation !",
                              body=f"L'évaluation de « {training['title']} » est disponible.",
                              user_training_id=user_training_id)

        # 3) Update the learner's learning-gap profile ------------------------
        try:
            gap = repo.get_learning_gap(user["id"])
            md, structured = update_learning_gap(
                gap.get("content", ""), gap.get("structured", {}) or {}, evaluation_json, objectives
            )
            repo.upsert_learning_gap(user["id"], md, structured)
            mlog.log_message(conv_id, mlog.ROLE_GAP_UPDATER, "Profil d'apprentissage mis à jour.",
                             internal=True, metadata={"content": md})
        except Exception as e:
            print(f"⚠️  gap-updater failed: {e}")
            md = repo.get_learning_gap(user["id"]).get("content", "")

        # 4) Initial feedback (Markdown) --------------------------------------
        try:
            agent = ChatAgent(evaluation_json, objectives_str, learning_gap=md)
            agent.create_initial_feedback(conversation_id=conv_id)
        except Exception as e:
            print(f"⚠️  initial feedback failed: {e}")
        repo.add_notification(user, "feedback_ready", "Agent de rétroaction !",
                              body=f"La rétroaction pour « {training['title']} » est disponible.",
                              user_training_id=user_training_id)

    except Exception as e:
        print(f"❌ completion pipeline failed for {user_training_id}: {e}")
        import traceback
        traceback.print_exc()
        try:
            repo.add_notification(user, "pipeline_error", "Un problème est survenu",
                                  body="Le traitement de votre évaluation a échoué. Veuillez réessayer.",
                                  user_training_id=user_training_id)
        except Exception:
            pass
