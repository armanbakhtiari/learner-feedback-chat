"use client";

import { useEffect, useState } from "react";
import { useApp } from "../AppContext";
import type { Suggestion } from "@/lib/types";

interface SuggestResponse {
  status: string;
  suggestions: Suggestion[];
  completed: { user_training_id: string; title: string }[];
  message?: string;
}

export default function SuggestionsView() {
  const { api, refreshTick, bump, toast, setTab, openTraining } = useApp();
  const [data, setData] = useState<SuggestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [picking, setPicking] = useState<string | null>(null);
  const [genFrom, setGenFrom] = useState<string>("");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .get<SuggestResponse>("/suggestions")
      .then((r) => active && setData(r))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, refreshTick]);

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
      const r = await api.post<{ user_training_id: string; title: string }>("/suggestions/generate", {
        user_training_id: genFrom,
      });
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

  if (loading) return <p className="text-slate-500">Chargement…</p>;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-1 text-2xl font-bold text-slate-800">Suggestions de formations</h1>
      <p className="mb-6 text-sm text-slate-500">
        Basées sur votre profil d&apos;apprentissage.
      </p>

      {/* Path 1 — bank suggestions */}
      <section className="mb-8">
        <h2 className="mb-3 font-semibold text-slate-700">Depuis la banque de formations</h2>
        {!data || data.suggestions.length === 0 ? (
          <p className="text-sm text-slate-500">
            {data?.message || "Aucune suggestion disponible pour le moment."}
          </p>
        ) : (
          <div className="space-y-3">
            {data.suggestions.map((s) => (
              <div key={s.training_id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="font-semibold text-slate-800">{s.title}</h3>
                <p className="mt-1 text-sm text-slate-600">{s.rationale}</p>
                <button
                  onClick={() => pick(s.training_id)}
                  disabled={picking === s.training_id}
                  className="mt-3 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
                >
                  {picking === s.training_id ? "Ajout…" : "➕ Ajouter au tableau de bord"}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Path 2 — generate new scenarios */}
      <section>
        <h2 className="mb-1 font-semibold text-slate-700">Créer de nouveaux scénarios</h2>
        <p className="mb-3 text-sm text-slate-500">
          Générez une nouvelle formation avec de nouveaux scénarios pour la situation d&apos;une
          formation déjà complétée, ciblant vos lacunes.
        </p>
        {data && data.completed.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={genFrom}
              onChange={(e) => setGenFrom(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand"
            >
              <option value="">Choisir une formation complétée…</option>
              {data.completed.map((c) => (
                <option key={c.user_training_id} value={c.user_training_id}>
                  {c.title}
                </option>
              ))}
            </select>
            <button
              onClick={generate}
              disabled={!genFrom || generating}
              className="rounded-lg border border-brand px-3 py-2 text-sm font-medium text-brand hover:bg-blue-50 disabled:opacity-50"
            >
              {generating ? "Génération… (peut prendre 1 min)" : "🛠️ Générer"}
            </button>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Complétez d&apos;abord une formation.</p>
        )}
      </section>
    </div>
  );
}
