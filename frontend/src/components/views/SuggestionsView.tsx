"use client";

import { useEffect, useState } from "react";
import { useApp } from "../AppContext";
import { IconRefresh, IconSparkle } from "../Icons";
import type { Suggestion } from "@/lib/types";

interface Completed {
  user_training_id: string;
  title: string;
}

export default function SuggestionsView() {
  const { api, refreshTick, bump, toast, setTab, openTraining } = useApp();
  const [completed, setCompleted] = useState<Completed[]>([]);
  const [loadingCompleted, setLoadingCompleted] = useState(true);

  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [picking, setPicking] = useState<string | null>(null);

  const [genFrom, setGenFrom] = useState("");
  const [generating, setGenerating] = useState(false);

  // On mount: only load the (cheap) completed list — do NOT run the LLM suggestions.
  useEffect(() => {
    let active = true;
    setLoadingCompleted(true);
    api
      .get<{ completed: Completed[] }>("/completed-list")
      .then((r) => active && setCompleted(r.completed))
      .finally(() => active && setLoadingCompleted(false));
    return () => {
      active = false;
    };
  }, [api, refreshTick]);

  const refreshSuggestions = async () => {
    setRefreshing(true);
    try {
      const r = await api.get<{ suggestions: Suggestion[] }>("/suggestions");
      setSuggestions(r.suggestions || []);
    } catch {
      toast("Impossible de générer des suggestions");
    } finally {
      setRefreshing(false);
    }
  };

  const pick = async (training_id: string) => {
    setPicking(training_id);
    try {
      await api.post("/suggestions/pick", { training_id });
      toast("Formation ajoutée à votre tableau de bord");
      bump();
      openTraining(null);
      setTab("dashboard");
    } catch {
      toast("Échec de l'ajout");
    } finally {
      setPicking(null);
    }
  };

  const generate = async () => {
    if (!genFrom) return;
    setGenerating(true);
    try {
      const r = await api.post<{ title: string }>("/suggestions/generate", { user_training_id: genFrom });
      toast(`Nouvelle formation créée : ${r.title}`);
      bump();
      openTraining(null);
      setTab("dashboard");
    } catch {
      toast("Échec de la génération");
    } finally {
      setGenerating(false);
    }
  };

  const hasCompleted = completed.length > 0;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Suggestions de formations</h1>
      <p className="mb-8 mt-1 text-sm text-slate-500">Basées sur votre profil d&apos;apprentissage.</p>

      {loadingCompleted ? (
        <p className="text-slate-500">Chargement…</p>
      ) : !hasCompleted ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-slate-600">
          Complétez au moins une formation pour recevoir des suggestions personnalisées.
        </div>
      ) : (
        <>
          {/* Path 1 — bank suggestions (on demand) */}
          <section className="mb-10">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Depuis la banque de formations</h2>
              <button
                onClick={refreshSuggestions}
                disabled={refreshing}
                className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
              >
                <IconRefresh />
                {refreshing ? "Analyse…" : "Actualiser les suggestions"}
              </button>
            </div>

            {suggestions === null ? (
              <p className="text-sm text-slate-500">
                Cliquez sur « Actualiser les suggestions » pour obtenir des recommandations basées sur vos lacunes.
              </p>
            ) : suggestions.length === 0 ? (
              <p className="text-sm text-slate-500">Aucune formation supplémentaire pertinente pour le moment.</p>
            ) : (
              <div className="space-y-3">
                {suggestions.map((s) => (
                  <div key={s.training_id} className="rounded-xl border border-slate-200 bg-white p-4">
                    <h3 className="font-semibold text-slate-800">{s.title}</h3>
                    <p className="mt-1 text-sm text-slate-600">{s.rationale}</p>
                    <button
                      onClick={() => pick(s.training_id)}
                      disabled={picking === s.training_id}
                      className="mt-3 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
                    >
                      {picking === s.training_id ? "Ajout…" : "Ajouter au tableau de bord"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Path 2 — generate new scenarios */}
          <section>
            <h2 className="font-semibold text-slate-800">Créer de nouveaux scénarios</h2>
            <p className="mb-3 mt-1 text-sm text-slate-500">
              Générez une nouvelle formation avec de nouveaux scénarios pour la situation d&apos;une formation déjà
              complétée, ciblant vos lacunes.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={genFrom}
                onChange={(e) => setGenFrom(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand"
              >
                <option value="">Choisir une formation complétée…</option>
                {completed.map((c) => (
                  <option key={c.user_training_id} value={c.user_training_id}>
                    {c.title}
                  </option>
                ))}
              </select>
              <button
                onClick={generate}
                disabled={!genFrom || generating}
                className="flex items-center gap-2 rounded-lg border border-brand px-3 py-2 text-sm font-medium text-brand transition hover:bg-blue-50 disabled:opacity-50"
              >
                <IconSparkle />
                {generating ? "Génération… (jusqu'à 1 min)" : "Générer"}
              </button>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
