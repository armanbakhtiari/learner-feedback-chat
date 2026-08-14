"use client";

import { useEffect, useState } from "react";
import { useApp } from "../AppContext";
import { IconClose, IconRefresh, IconSparkle } from "../Icons";
import type { Suggestion, TrainingPreview } from "@/lib/types";

interface Completed {
  user_training_id: string;
  title: string;
}

const DEFAULT_EMPTY_MESSAGE = "Aucune formation supplémentaire pertinente pour le moment.";

export default function SuggestionsView() {
  const { api, refreshTick, bump, toast, setTab, openTraining } = useApp();
  const [completed, setCompleted] = useState<Completed[]>([]);
  const [loadingCompleted, setLoadingCompleted] = useState(true);

  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [emptyMessage, setEmptyMessage] = useState(DEFAULT_EMPTY_MESSAGE);
  const [preference, setPreference] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [picking, setPicking] = useState<string | null>(null);

  const [preview, setPreview] = useState<TrainingPreview | null>(null);
  const [previewing, setPreviewing] = useState<string | null>(null);

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
      const wish = preference.trim();
      const r = await api.get<{ suggestions: Suggestion[]; message?: string }>(
        `/suggestions${wish ? `?preference=${encodeURIComponent(wish)}` : ""}`,
      );
      setSuggestions(r.suggestions || []);
      setEmptyMessage(r.message || DEFAULT_EMPTY_MESSAGE);
    } catch {
      toast("Impossible de générer des suggestions");
    } finally {
      setRefreshing(false);
    }
  };

  const showPreview = async (training_id: string) => {
    setPreviewing(training_id);
    try {
      setPreview(await api.get<TrainingPreview>(`/bank-trainings/${training_id}`));
    } catch {
      toast("Impossible d'afficher le contenu de cette formation");
    } finally {
      setPreviewing(null);
    }
  };

  const pick = async (training_id: string) => {
    setPicking(training_id);
    try {
      await api.post("/suggestions/pick", { training_id });
      toast("Formation ajoutée à votre tableau de bord");
      setPreview(null);
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
            <h2 className="mb-3 font-semibold text-slate-800">Depuis la banque de formations</h2>

            <div className="mb-4 flex flex-wrap items-center gap-2">
              <input
                value={preference}
                onChange={(e) => setPreference(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !refreshing) refreshSuggestions();
                }}
                placeholder="Optionnel : un sujet en particulier ? ex. « je voudrais des formations sur la migraine »"
                className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand"
              />
              <button
                onClick={refreshSuggestions}
                disabled={refreshing}
                className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
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
              <p className="text-sm text-slate-500">{emptyMessage}</p>
            ) : (
              <div className="space-y-3">
                {suggestions.map((s) => (
                  <div key={s.training_id} className="rounded-xl border border-slate-200 bg-white p-4">
                    <h3 className="font-semibold text-slate-800">{s.title}</h3>
                    <p className="mt-1 text-sm text-slate-600">{s.rationale}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        onClick={() => pick(s.training_id)}
                        disabled={picking === s.training_id}
                        className="rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
                      >
                        {picking === s.training_id ? "Ajout…" : "Ajouter au tableau de bord"}
                      </button>
                      <button
                        onClick={() => showPreview(s.training_id)}
                        disabled={previewing === s.training_id}
                        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                      >
                        {previewing === s.training_id ? "Chargement…" : "Voir le contenu"}
                      </button>
                    </div>
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

      {/* Content preview — objectives, situations and scenarios, never expert answers. */}
      {preview && (
        <div
          onClick={() => setPreview(null)}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 sm:p-8"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white shadow-lg"
          >
            <div className="flex items-start justify-between gap-4 border-b border-slate-200 p-4">
              <h3 className="font-semibold text-slate-800">{preview.title}</h3>
              <button
                onClick={() => setPreview(null)}
                aria-label="Fermer"
                className="shrink-0 rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              >
                <IconClose />
              </button>
            </div>

            <div className="max-h-[70vh] overflow-y-auto p-4">
              {preview.learning_objectives.length > 0 && (
                <div className="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
                  <p className="mb-1 font-semibold text-slate-700">Objectifs d&apos;apprentissage</p>
                  <ul className="list-disc pl-5">
                    {preview.learning_objectives.map((o, i) => (
                      <li key={i}>{o}</li>
                    ))}
                  </ul>
                </div>
              )}

              {preview.situations.map((sit, si) => (
                <div key={si} className="mb-5">
                  <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <span className="font-semibold">Situation :</span> {sit.text}
                  </div>
                  {sit.scenarios.map((sc, ci) => (
                    <div key={ci} className="mb-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                      <p className="mb-2 text-sm font-semibold text-slate-800">Scénario {ci + 1}</p>
                      <p className="mb-1 text-sm text-slate-700">
                        <span className="font-medium text-slate-500">Si vous pensiez …</span> {sc.hypothesis}
                      </p>
                      <p className="text-sm text-slate-700">
                        <span className="font-medium text-slate-500">Et qu&apos;alors …</span>{" "}
                        {sc.new_information}
                      </p>
                    </div>
                  ))}
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-200 p-4">
              <button
                onClick={() => setPreview(null)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              >
                Fermer
              </button>
              <button
                onClick={() => pick(preview.id)}
                disabled={picking === preview.id}
                className="rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
              >
                {picking === preview.id ? "Ajout…" : "Ajouter au tableau de bord"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
