"use client";

import { useEffect, useState } from "react";
import { useApp } from "../AppContext";
import EvalTable from "../EvalTable";
import { IconChat } from "../Icons";
import type { Conversation, UserTraining } from "@/lib/types";

export default function CompletedView() {
  const { api, refreshTick, conversations, openConversation } = useApp();
  const [trainings, setTrainings] = useState<UserTraining[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .get<{ trainings: UserTraining[] }>("/completed")
      .then((r) => active && setTrainings(r.trainings))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, refreshTick]);

  const convFor = (utId: string): Conversation | undefined =>
    conversations.find((c) => c.user_training_id === utId);

  if (loading) return <p className="text-slate-500">Chargement…</p>;

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Formations complétées</h1>
      <p className="mb-6 mt-1 text-sm text-slate-500">Votre évaluation et votre rétroaction pour chaque formation.</p>

      {trainings.length === 0 ? (
        <p className="text-slate-500">Aucune formation complétée pour le moment.</p>
      ) : (
        <div className="space-y-4">
          {trainings.map((ut) => {
            const conv = convFor(ut.id);
            const open = expanded === ut.id;
            return (
              <div key={ut.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="font-semibold text-slate-800">{ut.training?.title}</h3>
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-semibold text-green-700">
                    Complétée
                  </span>
                  <div className="ml-auto flex gap-2">
                    {conv && (
                      <button
                        onClick={() => openConversation(conv.id)}
                        className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                      >
                        <IconChat width={16} height={16} />
                        Ouvrir la rétroaction
                      </button>
                    )}
                    <button
                      onClick={() => setExpanded(open ? null : ut.id)}
                      className="rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
                    >
                      {open ? "Masquer l'évaluation" : "Voir l'évaluation"}
                    </button>
                  </div>
                </div>

                {open && (
                  <div className="mt-4 border-t border-slate-100 pt-4">
                    {ut.eval_table?.situations?.length ? (
                      <EvalTable table={ut.eval_table} />
                    ) : (
                      <p className="text-sm text-slate-500">
                        L&apos;évaluation est en cours de génération… vous serez notifié dès qu&apos;elle est prête.
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
