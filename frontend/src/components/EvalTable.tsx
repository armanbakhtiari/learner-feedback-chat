"use client";

import { useCallback, useEffect, useRef, useState, type PointerEvent } from "react";
import { IconChevronDown, IconClose, IconGrip } from "./Icons";
import ScenarioPrompt from "./ScenarioPrompt";
import type { EvalTable as EvalTableData, EvalTableRow } from "@/lib/types";

const COLUMNS = [
  "Scénario",
  "Éléments clés des experts",
  "Thèmes clés abordés",
  // The evaluator writes this column as optional avenues: joining one expert is enough.
  "Autres pistes des experts",
  "Raisonnement",
  "Communication",
];

/** Sober, non-judgmental styling — Learning-by-Concordance shows no scores or pass/fail. */
const th = "border-b border-slate-200 px-3 py-2 text-left text-xs font-semibold text-slate-600";
const td = "border-b border-slate-100 px-3 py-3 align-top text-slate-700";

/** Must match the panel's `max-w-2xl` / `w-[92vw]` / `max-h-[85vh]`, to open it centred. */
const PANEL_MAX_WIDTH = 672;
/** How much of the header must stay on screen so the panel can always be dragged back. */
const KEEP_VISIBLE = 120;

/**
 * A floating, draggable panel rather than a modal: there is no backdrop, so the table
 * underneath stays readable and scrollable while the learner compares the two.
 */
function ScenarioPanel({ row, onClose }: { row: EvalTableRow; onClose: () => void }) {
  const [pos, setPos] = useState(() => ({
    x: Math.max(8, (window.innerWidth - Math.min(PANEL_MAX_WIDTH, window.innerWidth * 0.92)) / 2),
    y: Math.max(8, window.innerHeight * 0.075),
  }));
  const [showExperts, setShowExperts] = useState(false);
  const drag = useRef<{ dx: number; dy: number } | null>(null);
  const experts = row.experts || [];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const startDrag = (e: PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("button")) return; // the close button
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { dx: e.clientX - pos.x, dy: e.clientY - pos.y };
  };
  const moveDrag = (e: PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    setPos({
      x: Math.min(Math.max(e.clientX - drag.current.dx, KEEP_VISIBLE - PANEL_MAX_WIDTH), window.innerWidth - KEEP_VISIBLE),
      y: Math.min(Math.max(e.clientY - drag.current.dy, 0), window.innerHeight - 56),
    });
  };
  const endDrag = (e: PointerEvent<HTMLDivElement>) => {
    drag.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  };

  return (
    <div
      role="dialog"
      aria-label="Scénario et réponses"
      style={{ left: pos.x, top: pos.y }}
      className="fixed z-50 max-h-[85vh] w-[92vw] max-w-2xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl"
    >
      <div
        onPointerDown={startDrag}
        onPointerMove={moveDrag}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        title="Glisser pour déplacer"
        className="flex h-14 cursor-move touch-none select-none items-center gap-2 border-b border-slate-200 bg-slate-50 px-5"
      >
        <IconGrip width={16} height={16} className="text-slate-400" />
        <span className="font-semibold text-slate-800">Scénario et réponses</span>
        <button
          onClick={onClose}
          aria-label="Fermer"
          className="ml-auto rounded p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
        >
          <IconClose width={18} height={18} />
        </button>
      </div>

      <div className="thin-scroll max-h-[calc(85vh-3.5rem)] overflow-y-auto p-5 text-sm">
        <ScenarioPrompt
          hypothesis={row.hypothesis}
          newInformation={row.new_information}
          kind={row.kind}
          scale={row.likert_scale}
        />

        <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Votre réponse
          </p>
          {row.response?.likert ? (
            <p className="mt-2">
              <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                {row.response.likert}
              </span>
            </p>
          ) : (
            <p className="mt-2 text-slate-500">Aucun niveau enregistré.</p>
          )}
          <p className="mt-3 whitespace-pre-wrap text-slate-700">
            {row.response?.justification || "Aucune justification fournie."}
          </p>
        </div>

        {experts.length > 0 && (
          <div className="mt-4 rounded-lg border border-slate-200">
            <button
              onClick={() => setShowExperts((v) => !v)}
              aria-expanded={showExperts}
              className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              <IconChevronDown
                width={16}
                height={16}
                className={`text-slate-400 transition ${showExperts ? "rotate-180" : ""}`}
              />
              {showExperts ? "Masquer" : "Voir"} les réponses des experts ({experts.length})
            </button>
            {showExperts && (
              <div className="border-t border-slate-200 px-4 py-3">
                <p className="mb-3 text-xs text-slate-500">
                  Chaque expert propose un angle — rejoindre l&apos;un d&apos;eux suffit.
                </p>
                <ul className="space-y-4">
                  {experts.map((e, i) => (
                    <li key={i}>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-semibold text-slate-700">{e.expert_label}</span>
                        {e.likert && (
                          <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                            {e.likert}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 whitespace-pre-wrap text-slate-700">{e.justification}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function EvalTable({ table }: { table: EvalTableData }) {
  const [viewing, setViewing] = useState<EvalTableRow | null>(null);
  const closeViewing = useCallback(() => setViewing(null), []);

  return (
    <div className="space-y-6">
      {table.situations.map((situation, i) => (
        <div key={i}>
          <h4 className="text-sm font-semibold text-slate-800">{situation.title}</h4>
          {situation.description && (
            <p className="mt-0.5 text-xs text-slate-500">{situation.description}</p>
          )}

          <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full min-w-[52rem] border-collapse text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c} className={th}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {situation.scenarios.map((row) => (
                  <tr key={row.scenario_id}>
                    <td className={`${td} min-w-52`}>
                      <p className="text-slate-800">{row.hypothesis}</p>
                      <button
                        onClick={() => setViewing(row)}
                        className="mt-2 rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                      >
                        Voir le scénario et les réponses
                      </button>
                    </td>
                    <td className={td}>
                      {row.expert_key_elements.length > 0 ? (
                        <ul className="list-disc space-y-1 pl-4">
                          {row.expert_key_elements.map((el, j) => (
                            <li key={j}>{el}</li>
                          ))}
                        </ul>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className={td}>{row.themes_addressed || "—"}</td>
                    <td className={td}>{row.themes_missed || "—"}</td>
                    <td className={td}>{row.reasoning || "—"}</td>
                    <td className={td}>{row.communication || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {viewing && <ScenarioPanel row={viewing} onClose={closeViewing} />}
    </div>
  );
}
