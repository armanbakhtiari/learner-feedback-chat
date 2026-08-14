"use client";

import { useCallback, useEffect, useState } from "react";
import { useApp } from "../AppContext";
import Markdown from "../Markdown";
import { IconHistory } from "../Icons";
import type { LearningGapVersion } from "@/lib/types";

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString("fr-CA", {
    dateStyle: "long",
    timeStyle: "short",
  });

export default function LearningView() {
  const { api, refreshTick, bump } = useApp();
  const [content, setContent] = useState("");
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // Distinguish a failed load from a genuinely empty profile.
  const [failed, setFailed] = useState(false);

  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<LearningGapVersion[] | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [openVersion, setOpenVersion] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setFailed(false);
    api
      .get<{ content: string; updated_at: string | null }>("/learning-gaps")
      .then((r) => {
        if (!active) return;
        setContent(r.content);
        setUpdatedAt(r.updated_at);
      })
      .catch(() => active && setFailed(true))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, refreshTick]);

  // A new evaluation adds a version, so drop the cache whenever the app ticks.
  useEffect(() => {
    setHistory(null);
    setOpenVersion(null);
  }, [refreshTick]);

  const toggleHistory = useCallback(async () => {
    const next = !showHistory;
    setShowHistory(next);
    if (!next || history) return;
    setHistoryLoading(true);
    try {
      const r = await api.get<{ history: LearningGapVersion[] }>("/learning-gaps/history");
      setHistory(r.history);
    } finally {
      setHistoryLoading(false);
    }
  }, [showHistory, history, api]);

  if (loading) return <p className="text-slate-500">Chargement…</p>;

  if (failed)
    return (
      <div className="mx-auto max-w-3xl rounded-xl border border-slate-200 bg-white p-6">
        <p className="text-slate-600">Impossible de charger votre profil d&apos;apprentissage.</p>
        <button
          onClick={bump}
          className="mt-3 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90"
        >
          Réessayer
        </button>
      </div>
    );

  // The newest history row mirrors the current profile — show the older ones as "previous".
  const previous = (history ?? []).slice(1);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Mon apprentissage</h1>
      <p className="mb-6 mt-1 text-sm text-slate-500">
        Votre profil de lacunes, mis à jour après chaque évaluation.
        {updatedAt && ` Dernière mise à jour : ${formatDate(updatedAt)}.`}
      </p>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        {content.trim() ? (
          <Markdown>{content}</Markdown>
        ) : (
          <p className="text-slate-500">
            Votre profil se construira au fur et à mesure de vos formations complétées.
          </p>
        )}
      </div>

      <div className="mt-6">
        <button
          onClick={toggleHistory}
          className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        >
          <IconHistory width={16} height={16} />
          {showHistory ? "Masquer mes versions précédentes" : "Voir mes versions précédentes"}
        </button>

        {showHistory && (
          <div className="mt-4">
            {historyLoading ? (
              <p className="text-sm text-slate-500">Chargement de l&apos;historique…</p>
            ) : previous.length === 0 ? (
              <p className="text-sm text-slate-500">
                Aucune version précédente — votre profil n&apos;a été mis à jour qu&apos;une seule fois.
              </p>
            ) : (
              <ul className="space-y-3">
                {previous.map((version) => {
                  const open = openVersion === version.id;
                  return (
                    <li
                      key={version.id}
                      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                    >
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="text-sm font-medium text-slate-800">
                          Version du {formatDate(version.created_at)}
                        </span>
                        <button
                          onClick={() => setOpenVersion(open ? null : version.id)}
                          className="ml-auto rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                        >
                          {open ? "Masquer" : "Voir"}
                        </button>
                      </div>
                      {open && (
                        <div className="mt-4 border-t border-slate-100 pt-4">
                          {version.content.trim() ? (
                            <Markdown>{version.content}</Markdown>
                          ) : (
                            <p className="text-sm text-slate-500">Profil vide à cette date.</p>
                          )}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
