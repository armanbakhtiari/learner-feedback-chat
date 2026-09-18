"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useApp } from "../AppContext";
import { IconArrowLeft, IconSparkle } from "../Icons";
import { likertValues, type Likert, type Scenario, type Training, type UserTraining } from "@/lib/types";

type Answer = { likert: Likert | null; justification: string };
type SaveState = "idle" | "dirty" | "saving" | "saved" | "error";

const EVAL_PROGRESS_MESSAGES = [
  "Analyse de vos réponses…",
  "Génération du tableau d'évaluation…",
  "Mise à jour de votre profil d'apprentissage…",
  "Rédaction du retour initial…",
];

const SAVE_LABELS: Record<SaveState, string> = {
  idle: "",
  dirty: "Modifications non enregistrées",
  saving: "Enregistrement…",
  saved: "Brouillon enregistré",
  error: "Échec de l'enregistrement",
};

/** The single rule for "this scenario is answered" — the backend applies the same one. */
const isAnswered = (a?: Answer) => Boolean(a?.likert && (a.justification || "").trim());

/** Answers are saved on their own a moment after the learner stops typing. */
const AUTOSAVE_DELAY_MS = 1500;

export default function TrainingView({ userTrainingId }: { userTrainingId: string }) {
  const { api, openTraining, setTab, toast, bump } = useApp();
  const [training, setTraining] = useState<Training | null>(null);
  const [status, setStatus] = useState<UserTraining["status"]>("not_started");
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [assisting, setAssisting] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [evalProgress, setEvalProgress] = useState(0);
  const [loading, setLoading] = useState(true);

  // Latest answers, readable from callbacks that must not be re-created on every keystroke.
  const answersRef = useRef<Record<string, Answer>>({});
  answersRef.current = answers;
  // A save the component itself triggered (seeding, merging) must not look like an edit.
  const skipAutosave = useRef(true);
  const savingRef = useRef(false);

  useEffect(() => {
    if (!evaluating) {
      setEvalProgress(0);
      return;
    }
    const id = setInterval(() => {
      setEvalProgress((i) => Math.min(i + 1, EVAL_PROGRESS_MESSAGES.length - 1));
    }, 60_000);
    return () => clearInterval(id);
  }, [evaluating]);

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
        skipAutosave.current = true;
        setAnswers(init);
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, userTrainingId]);

  // Scenario numbering restarts inside each situation, exactly as the headings below show
  // it — so build the learner-facing label while flattening, and never recompute it apart.
  const multiSituation = (training?.situations || []).length > 1;
  const flat = useMemo(() => {
    const out: { sc: Scenario; label: string }[] = [];
    (training?.situations || []).forEach((sit, sIdx) =>
      sit.scenarios.forEach((sc, idx) =>
        out.push({
          sc,
          label: multiSituation
            ? `Situation ${sIdx + 1}, scénario ${idx + 1}`
            : `Scénario ${idx + 1}`,
        }),
      ),
    );
    return out;
  }, [training, multiSituation]);
  const scenarios = useMemo(() => flat.map((f) => f.sc), [flat]);
  // The response scale is a property of the training, not a global constant.
  const scaleValues = useMemo(() => likertValues(training?.likert_scale), [training]);
  const missing = useMemo(() => flat.filter((f) => !isAnswered(answers[f.sc.id])), [flat, answers]);
  const allAnswered = missing.length === 0;

  const setAnswer = (id: string, patch: Partial<Answer>) =>
    setAnswers((a) => ({ ...a, [id]: { ...a[id], ...patch } }));

  const payload = useCallback(
    () =>
      scenarios.map((sc) => ({
        scenario_id: sc.id,
        likert: answersRef.current[sc.id]?.likert ?? null,
        justification: answersRef.current[sc.id]?.justification ?? null,
      })),
    [scenarios],
  );

  const persist = useCallback(
    async (auto: boolean) => {
      if (savingRef.current) return;
      savingRef.current = true;
      setSaveState("saving");
      if (!auto) setSaving(true);
      try {
        await api.put(`/trainings/${userTrainingId}/responses`, { responses: payload() });
        setSaveState("saved");
        setStatus((s) => (s === "not_started" ? "in_progress" : s));
        // Only a deliberate save refreshes the rest of the UI — an autosave firing while
        // the learner types must not make the dashboard refetch every second.
        if (!auto) {
          toast("Brouillon enregistré");
          bump();
        }
      } catch (e) {
        setSaveState("error");
        if (!auto) toast("Échec de l'enregistrement");
        console.error(e);
      } finally {
        savingRef.current = false;
        if (!auto) setSaving(false);
      }
    },
    [api, bump, payload, toast, userTrainingId],
  );

  // Autosave: answers used to live only in this tab's memory until the learner pressed
  // "Enregistrer le brouillon", so navigating away or reloading lost them silently.
  useEffect(() => {
    if (skipAutosave.current) {
      skipAutosave.current = false;
      return;
    }
    if (status === "completed" || evaluating) return;
    setSaveState("dirty");
    const t = setTimeout(() => void persist(true), AUTOSAVE_DELAY_MS);
    return () => clearTimeout(t);
  }, [answers, evaluating, persist, status]);

  // A tab left open can hold a stale draft while another one saves newer answers. Re-read
  // the server copy when the learner comes back and merge it in — a filled field always
  // wins over an empty one, whichever side it is on.
  useEffect(() => {
    const sync = async () => {
      if (document.visibilityState !== "visible") return;
      if (savingRef.current || evaluating || status === "completed") return;
      try {
        const r = await api.get<{ user_training: UserTraining; training: Training }>(
          `/trainings/${userTrainingId}`,
        );
        const server: Record<string, Answer> = {};
        for (const sit of r.training.situations || [])
          for (const sc of sit.scenarios)
            server[sc.id] = {
              likert: sc.response?.likert ?? null,
              justification: sc.response?.justification ?? "",
            };
        setAnswers((prev) => {
          const merged: Record<string, Answer> = {};
          for (const [id, s] of Object.entries(server)) {
            const localText = (prev[id]?.justification || "").trim();
            merged[id] = {
              likert: prev[id]?.likert ?? s.likert,
              justification: localText ? prev[id].justification : s.justification,
            };
          }
          if (JSON.stringify(merged) === JSON.stringify(prev)) return prev;
          skipAutosave.current = true;
          return merged;
        });
      } catch {
        /* transient; the next focus retries */
      }
    };
    document.addEventListener("visibilitychange", sync);
    window.addEventListener("focus", sync);
    return () => {
      document.removeEventListener("visibilitychange", sync);
      window.removeEventListener("focus", sync);
    };
  }, [api, evaluating, status, userTrainingId]);

  const goToMissing = () => {
    const first = missing[0];
    if (!first) return;
    document
      .getElementById(`scenario-${first.sc.id}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const saveDraft = () => persist(false);

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
      toast("Évaluation terminée.");
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

  const answeredCount = scenarios.length - missing.length;

  return (
    <div className="mx-auto max-w-3xl">
      <button
        onClick={() => openTraining(null)}
        className="mb-3 flex items-center gap-1.5 text-sm text-slate-500 transition hover:text-slate-700"
      >
        <IconArrowLeft />
        Retour
      </button>
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-slate-900">{training.title}</h1>
      <div className="mb-5 rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-600">
        <p className="mb-1 font-semibold text-slate-700">Objectifs d&apos;apprentissage</p>
        <ul className="list-disc pl-5">
          {(training.learning_objectives || []).map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ul>
      </div>

      {(training.situations || []).map((sit, sIdx) => (
        <div key={sit.id} className="mb-6">
          <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            {/* A training can carry several situations, and scenario numbering restarts
                inside each one — so name the situation or they are indistinguishable. */}
            <p className="mb-1 font-semibold text-slate-800">
              {multiSituation ? `Situation ${sIdx + 1}` : "Situation"}
              {sit.title ? ` — ${sit.title}` : ""}
            </p>
            {sit.text}
          </div>
          {sit.scenarios.map((sc, idx) => {
            const a = answers[sc.id] || { likert: null, justification: "" };
            const incomplete = !isAnswered(a);
            return (
              <div
                key={sc.id}
                id={`scenario-${sc.id}`}
                className={`mb-4 scroll-mt-4 rounded-xl border bg-white p-4 shadow-sm ${
                  incomplete ? "border-amber-300" : "border-slate-200"
                }`}
              >
                <p className="mb-2 flex items-center gap-2 text-sm">
                  <span className="font-semibold text-slate-800">Scénario {idx + 1}</span>
                  {incomplete && (
                    <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                      À compléter
                    </span>
                  )}
                </p>
                <p className="mb-1 text-sm text-slate-700">
                  <span className="font-medium text-slate-500">Si vous pensiez …</span> {sc.hypothesis}
                </p>
                <p className="mb-3 text-sm text-slate-700">
                  <span className="font-medium text-slate-500">Et qu&apos;alors …</span> {sc.new_information}
                </p>

                <div className="mb-3 flex flex-wrap gap-1.5">
                  {scaleValues.map((lv) => (
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
                    onBlur={() => {
                      if (status !== "completed" && !evaluating) void persist(true);
                    }}
                    placeholder="Votre justification…"
                    rows={3}
                    className="w-full resize-y rounded-lg border border-slate-300 p-2.5 pr-10 text-sm outline-none focus:border-brand"
                  />
                  <button
                    onClick={() => runAssist(sc.id)}
                    disabled={assisting === sc.id}
                    title="Générer une réponse avec l'assistant IA"
                    className="absolute right-2 top-2 flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-slate-500 transition hover:bg-slate-50 hover:text-brand disabled:opacity-50"
                  >
                    <IconSparkle />
                    {assisting === sc.id ? "…" : "Assistant"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ))}

      <div className="sticky bottom-0 flex flex-wrap items-center gap-3 border-t border-slate-200 bg-[var(--background)] py-3">
        <button
          onClick={saveDraft}
          disabled={saving || evaluating}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {saving ? "Enregistrement…" : "Enregistrer le brouillon"}
        </button>
        <button
          onClick={evaluate}
          disabled={!allAnswered || evaluating || saving}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40"
          title={allAnswered ? "" : "Répondez à tous les scénarios (niveau + justification)"}
        >
          {evaluating ? EVAL_PROGRESS_MESSAGES[evalProgress] : "Évaluer"}
        </button>
        {!allAnswered && (
          <span className="text-xs text-slate-500">
            {answeredCount} scénario{answeredCount > 1 ? "s" : ""} sur {scenarios.length} complété
            {answeredCount > 1 ? "s" : ""}.{" "}
            <button onClick={goToMissing} className="font-medium text-brand underline">
              {missing.length > 1
                ? "Aller au premier scénario à compléter"
                : `Aller au scénario à compléter (${missing[0].label.toLowerCase()})`}
            </button>
          </span>
        )}
        {saveState !== "idle" && (
          <span
            className={`ml-auto text-xs ${saveState === "error" ? "text-amber-700" : "text-slate-400"}`}
          >
            {SAVE_LABELS[saveState]}
          </span>
        )}
      </div>
    </div>
  );
}
