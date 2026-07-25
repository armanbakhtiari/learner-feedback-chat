"use client";

import { useEffect, useState } from "react";
import { useApp } from "../AppContext";
import Markdown from "../Markdown";

export default function LearningView() {
  const { api, refreshTick } = useApp();
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .get<{ content: string }>("/learning-gaps")
      .then((r) => active && setContent(r.content))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, refreshTick]);

  if (loading) return <p className="text-slate-500">Chargement…</p>;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Mon apprentissage</h1>
      <p className="mb-6 mt-1 text-sm text-slate-500">
        Votre profil de lacunes, mis à jour après chaque évaluation.
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
    </div>
  );
}
