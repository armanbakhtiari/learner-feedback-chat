"use client";

import { useEffect, useMemo, useState } from "react";
import { useApp } from "../AppContext";
import { LIKERT_VALUES, type Likert, type Training, type UserTraining } from "@/lib/types";

type Answer = { likert: Likert | null; justification: string };

export default function TrainingView({ userTrainingId }: { userTrainingId: string }) {
  const { api, openTraining, setTab, toast, bump } = useApp();
  const [training, setTraining] = useState<Training | null>(null);
  const [status, setStatus] = useState<UserTraining["status"]>("not_started");
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [assisting, setAssisting] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .get<{ user_training: UserTraining; training: Training }>(`/trainings/${userTrainingId}`)
      .then((r) => {
        if (!active) return;
        setTraining(r.training);
        setStatus(r.user_training.status);
        const init: Record<string, Answer> = {};
        for (const sit of r.training.situations || [])
          for (const sc of sit.scenarios)
            init[sc.id] = {
              likert: sc.response?.likert ?? null,
              justification: sc.response?.justification ?? "",
            };
        setAnswers(init);
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, userTrainingId]);

  const scenarios = useMemo(
    () => (training?.situations || []).flatMap((s) => s.scenarios),
    [training],
  );
  const allAnswered = scenarios.every(
    (sc) => answers[sc.id]?.likert && (answers[sc.id]?.justification || "").trim(),
  );

  const setAnswer = (id: string, patch: Partial<Answer>) =>
    setAnswers((a) => ({ ...a, [id]: { ...a[id], ...patch } }));

  const payload = () =>
    scenarios.map((sc) => ({
      scenario_id: sc.id,
      likert: answers[sc.id]?.likert ?? null,
      justification: answers[sc.id]?.justification ?? null,
    }));

  const saveDraft = async () => {
    setSaving(true);
    try {
      await api.put(`/trainings/${userTrainingId}/responses`, { responses: payload() });
      toast("Brouillon enregistré");
      setStatus("in_progress");
      bump();
    } catch (e) {
      toast("Échec de l'enregistrement");
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const runAssist = async (scenarioId: string) => {
    setAssisting(scenarioId);
    try {
      const r = await api.post<{ likert: Likert; justification: string }>(
        `/trainings/${userTrainingId}/assist`,
        { scenario_id: scenarioId },
      );
      setAnswer(scenarioId, { likert: r.likert, justification: r.justification });
    } catch {
      toast("L'assistant n'a pas pu générer de réponse");
    } finally {
      setAssisting(null);
    }
  };

  const evaluate = async () => {
    setEvaluating(true);
    try {
      await api.put(`/trainings/${userTrainingId}/responses`, { responses: payload() });
      await api.post(`/trainings/${userTrainingId}/evaluate`);
      toast("Évaluation lancée — vous serez notifié dès qu'elle est prête.");
      bump();
      openTraining(null);
      setTab("completed");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Échec de l'évaluation");
    } finally {
      setEvaluating(false);
    }
  };

  if (loading) return <p className="text-slate-500">Chargement…</p>;
  if (!training) return <p className="text-slate-500">Formation introuvable.</p>;

  return (
    <div className="mx-auto max-w-3xl">
      <button onClick={() => openTraining(null)} className="mb-3 text-sm text-slate-500 hover:text-slate-700">
        ← Retour
      </button>
      <h1 className="mb-1 text-2xl font-bold text-slate-800">{training.title}</h1>
      <div className="mb-5 rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-600">
        <p className="mb-1 font-semibold text-slate-700">Objectifs d&apos;apprentissage</p>
        <ul className="list-disc pl-5">
          {(training.learning_objectives || []).map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ul>
      </div>

      {(training.situations || []).map((sit) => (
        <div key={sit.id} className="mb-6">
          <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <span className="font-semibold">Situation :</span> {sit.text}
          </div>
          {sit.scenarios.map((sc, idx) => {
            const a = answers[sc.id] || { likert: null, justification: "" };
            return (
              <div key={sc.id} className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <p className="mb-2 text-sm">
                  <span className="font-semibold text-slate-800">Scénario {idx + 1}</span>
                </p>
                <p className="mb-1 text-sm text-slate-700">
                  <span className="font-medium text-slate-500">Si vous pensiez …</span> {sc.hypothesis}
                </p>
                <p className="mb-3 text-sm text-slate-700">
                  <span className="font-medium text-slate-500">Et qu&apos;alors …</span> {sc.new_information}
                </p>

                <div className="mb-3 flex flex-wrap gap-1.5">
                  {LIKERT_VALUES.map((lv) => (
                    <button
                      key={lv}
                      onClick={() => setAnswer(sc.id, { likert: lv })}
                      className={`rounded-full border px-3 py-1 text-xs font-medium ${
                        a.likert === lv
                          ? "border-brand bg-brand text-white"
                          : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      {lv}
                    </button>
                  ))}
                </div>

                <div className="relative">
                  <textarea
                    value={a.justification}
                    onChange={(e) => setAnswer(sc.id, { justification: e.target.value })}
                    placeholder="Votre justification…"
                    rows={3}
                    className="w-full resize-y rounded-lg border border-slate-300 p-2.5 pr-10 text-sm outline-none focus:border-brand"
                  />
                  <button
                    onClick={() => runAssist(sc.id)}
                    disabled={assisting === sc.id}
                    title="Générer une réponse avec l'assistant IA"
                    className="absolute right-2 top-2 rounded-md px-1.5 py-1 text-lg hover:bg-slate-100 disabled:opacity-50"
                  >
                    {assisting === sc.id ? "⏳" : "🤖"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ))}

      <div className="sticky bottom-0 flex items-center gap-3 border-t border-slate-200 bg-[var(--background)] py-3">
        <button
          onClick={saveDraft}
          disabled={saving || evaluating}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {saving ? "Enregistrement…" : "💾 Enregistrer le brouillon"}
        </button>
        <button
          onClick={evaluate}
          disabled={!allAnswered || evaluating || saving}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40"
          title={allAnswered ? "" : "Répondez à tous les scénarios (niveau + justification)"}
        >
          {evaluating ? "Lancement…" : "✅ Évaluer"}
        </button>
        {!allAnswered && (
          <span className="text-xs text-slate-400">Répondez à tous les scénarios pour évaluer.</span>
        )}
      </div>
    </div>
  );
}
