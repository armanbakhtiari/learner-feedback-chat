"use client";

import { useEffect, useState } from "react";
import { useApp } from "../AppContext";
import type { UserTraining } from "@/lib/types";

export default function DashboardView() {
  const { api, refreshTick, bump, openTraining } = useApp();
  const [trainings, setTrainings] = useState<UserTraining[]>([]);
  const [loading, setLoading] = useState(true);
  // A failed load must not look like "you have no trainings" — that is
  // indistinguishable from the real empty state and only a manual refresh fixed it.
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setFailed(false);
    api
      .get<{ trainings: UserTraining[] }>("/dashboard")
      .then((r) => active && setTrainings(r.trainings))
      .catch(() => active && setFailed(true))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, refreshTick]);

  if (loading) return <p className="text-slate-500">Chargement…</p>;

  if (failed)
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <p className="text-slate-600">Impossible de charger vos formations.</p>
        <button
          onClick={bump}
          className="mt-3 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90"
        >
          Réessayer
        </button>
      </div>
    );

  // The entry-point trainings are a choice, not a checklist — completing any one of them
  // is what unlocks the rétroaction and the suggestions.
  const mandatoryCount = trainings.filter((ut) => ut.training?.origin === "seed_mandatory").length;

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Tableau de bord</h1>
      <p className="mb-6 mt-1 text-sm text-slate-500">
        Vos formations à compléter.
        {mandatoryCount > 1 && (
          <>
            {" "}
            Plusieurs formations d&apos;entrée vous sont proposées : complétez celle de votre choix
            pour accéder à la rétroaction et aux suggestions.
          </>
        )}
      </p>

      {trainings.length === 0 ? (
        <p className="text-slate-500">Aucune formation en attente. Consultez l&apos;onglet Suggestions.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {trainings.map((ut) => {
            const mandatory = ut.training?.origin === "seed_mandatory";
            return (
              <button
                key={ut.id}
                onClick={() => openTraining(ut.id)}
                className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-brand hover:shadow"
              >
                <div className="mb-2 flex items-center gap-2">
                  {mandatory && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                      Formation obligatoire — au choix
                    </span>
                  )}
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                      ut.status === "in_progress"
                        ? "bg-blue-100 text-blue-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {ut.status === "in_progress" ? "En cours" : "À commencer"}
                  </span>
                </div>
                <h3 className="mb-1 font-semibold text-slate-800">{ut.training?.title}</h3>
                <p className="line-clamp-3 text-xs text-slate-500">
                  {(ut.situation_titles || []).join(" · ")}
                </p>
                <span className="mt-3 text-sm font-medium text-brand">Ouvrir →</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
