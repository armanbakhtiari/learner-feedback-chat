"use client";

import { useApp } from "../AppContext";
import { IconChat } from "../Icons";

/** Feedback conversations, one per completed training. Selecting one opens it full-screen. */
export default function FeedbackView() {
  const { conversations, openConversation } = useApp();

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Agent de rétroaction</h1>
      <p className="mb-6 mt-1 text-sm text-slate-500">
        Vos échanges avec l&apos;agent, une conversation par formation complétée.
      </p>

      {conversations.length === 0 ? (
        <p className="text-slate-500">
          Aucune conversation. Complétez une formation pour recevoir une rétroaction.
        </p>
      ) : (
        <div className="space-y-4">
          {conversations.map((c) => (
            <div key={c.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-center gap-3">
                <h3 className="font-semibold text-slate-800">{c.title}</h3>
                <span className="text-[11px] text-slate-400">
                  {new Date(c.created_at).toLocaleString("fr-CA")}
                </span>
                <button
                  onClick={() => openConversation(c.id)}
                  className="ml-auto flex items-center gap-2 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90"
                >
                  <IconChat width={16} height={16} />
                  Ouvrir la rétroaction
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
