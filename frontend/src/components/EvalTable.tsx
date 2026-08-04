"use client";

import { useState } from "react";
import { IconClose } from "./Icons";
import type { EvalTable as EvalTableData, EvalTableRow } from "@/lib/types";

const COLUMNS = [
  "Scénario",
  "Éléments clés des experts",
  "Thèmes clés abordés",
  "Thèmes clés manqués",
  "Raisonnement",
  "Communication",
];

/** Sober, non-judgmental styling — Learning-by-Concordance shows no scores or pass/fail. */
const th = "border-b border-slate-200 px-3 py-2 text-left text-xs font-semibold text-slate-600";
const td = "border-b border-slate-100 px-3 py-3 align-top text-slate-700";

function ScenarioModal({ row, onClose }: { row: EvalTableRow; onClose: () => void }) {
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[92vw] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
        <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-5">
          <span className="font-semibold text-slate-800">Scénario et votre réponse</span>
          <button
            onClick={onClose}
            className="ml-auto rounded p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          >
            <IconClose width={18} height={18} />
          </button>
        </div>

        <div className="thin-scroll max-h-[calc(85vh-3.5rem)] overflow-y-auto p-5 text-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Si vous pensiez…
          </p>
          <p className="mt-1 text-slate-800">{row.hypothesis}</p>

          <p className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Et qu&apos;alors…
          </p>
          <p className="mt-1 whitespace-pre-wrap text-slate-800">{row.new_information}</p>

          <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
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
        </div>
      </div>
    </>
  );
}

export default function EvalTable({ table }: { table: EvalTableData }) {
  const [viewing, setViewing] = useState<EvalTableRow | null>(null);

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
                        Voir le scénario et ma réponse
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

      {viewing && <ScenarioModal row={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}
