"""
Evaluation-table builder (structured, deterministic — no LLM).

Turns the evaluator's structured JSON into the table shown in the "Complétées" tab.
This used to be an LLM that authored a freeform HTML fragment; it now zips the
evaluation with the training content so every row carries its real `scenario_id`,
the scenario text, and the learner's own answer — which is what lets the UI offer a
"Voir" button per row. Rendering moved to React (`frontend/src/components/EvalTable.tsx`).

The evaluator's keys ("situation 1", "scenario 2", ...) are positional and follow the
exact order `training_parser.build_evaluation_input` fed it: situations by
`situation_index`, scenarios by `scenario_index` — which is also the order
`repo.get_training_content()` returns. So the zip below is a faithful mapping, not a guess.

Each row also carries the expert panel's answers, which the "Voir" modal reveals on
demand. This table is only ever served for a *completed* training — after answering,
comparing one's reasoning with the experts' is the point of Learning by Concordance — so
it is the one client path expert responses are allowed to reach. The educational
synthesis stays out of it.

Learning-by-Concordance stays non-judgmental: qualitative summaries only, no numeric
scores, no pass/fail labels.
"""

import re
from typing import Any, Dict, List, Optional


def _expert_order(expert: Dict[str, Any]) -> tuple:
    """'Expert 2' before 'Expert 10' — the rows come back from the DB unordered."""
    label = expert.get("expert_label") or ""
    m = re.search(r"\d+", label)
    return (int(m.group()) if m else 0, label)


def _experts(scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "expert_label": e.get("expert_label", ""),
            "likert": e.get("likert"),
            "justification": e.get("justification", ""),
        }
        for e in sorted(scenario.get("experts") or [], key=_expert_order)
    ]


def _split_coverage(justification: str) -> tuple[str, str]:
    """
    The evaluator writes coverage.justification as two lines: line 1 = themes the
    learner addressed, line 2 = critical expert themes they missed. Fall back to
    treating the whole text as "addressed" when the model didn't split it.
    """
    text = (justification or "").strip()
    if not text:
        return "", ""
    parts = [p.strip() for p in text.split("\n", 1)]
    if len(parts) == 2 and parts[1]:
        return parts[0], parts[1]
    return parts[0], ""


def build_eval_table(
    evaluation_json: Dict[str, Any],
    training_content: Dict[str, Any],
    responses: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build the structured evaluation table.

    ``training_content`` is ``repo.get_training_content(training_id, include_experts=True)``
    (situations -> scenarios, ordered); ``responses`` maps scenario id -> {likert,
    justification}. Without experts loaded, rows simply carry an empty panel.
    """
    ev_situations = (evaluation_json or {}).get("situations", {}) or {}
    out: List[Dict[str, Any]] = []

    for s_i, sit in enumerate(training_content.get("situations", []), start=1):
        ev_sit = ev_situations.get(f"situation {s_i}") or {}
        ev_scenarios = ev_sit.get("scenarios", {}) or {}

        rows: List[Dict[str, Any]] = []
        for c_i, sc in enumerate(sit.get("scenarios", []), start=1):
            ev_sc = ev_scenarios.get(f"scenario {c_i}")
            if not ev_sc:
                continue  # evaluator skipped it; nothing qualitative to show
            addressed, missed = _split_coverage((ev_sc.get("coverage") or {}).get("justification", ""))
            resp = responses.get(sc["id"]) or {}
            rows.append({
                "scenario_id": sc["id"],
                "kind": sc.get("kind") or "reasoning",
                "likert_scale": sc.get("likert_scale") or training_content.get("likert_scale"),
                "hypothesis": sc.get("hypothesis", ""),
                "new_information": sc.get("new_information", ""),
                "response": {
                    "likert": resp.get("likert"),
                    "justification": resp.get("justification"),
                },
                "expert_key_elements": ev_sc.get("expert_key_elements") or [],
                "themes_addressed": addressed,
                "themes_missed": missed,
                "reasoning": (ev_sc.get("logical_reasoning") or {}).get("assessment", ""),
                "communication": (ev_sc.get("communication") or {}).get("assessment", ""),
                "experts": _experts(sc),
            })

        if rows:
            out.append({
                "title": sit.get("title") or f"Situation {s_i}",
                "description": ev_sit.get("description", ""),
                "scenarios": rows,
            })

    return {"situations": out}
