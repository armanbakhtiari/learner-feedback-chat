"use client";

import { useApp } from "./AppContext";
import { IconChat, IconClose } from "./Icons";

/** Right-side drawer listing feedback conversations. Selecting one opens it full-screen. */
export default function FeedbackDrawer() {
  const { drawerOpen, setDrawerOpen, conversations, openConversation } = useApp();

  if (!drawerOpen) return null;

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20" onClick={() => setDrawerOpen(false)} />
      <aside className="fixed right-0 top-0 z-50 flex h-full w-full max-w-sm flex-col border-l border-slate-200 bg-white shadow-xl">
        <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-5">
          <IconChat width={18} height={18} />
          <span className="font-semibold text-slate-800">Rétroactions</span>
          <button
            onClick={() => setDrawerOpen(false)}
            className="ml-auto rounded p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          >
            <IconClose width={18} height={18} />
          </button>
        </div>

        <div className="thin-scroll flex-1 overflow-y-auto p-3">
          {conversations.length === 0 ? (
            <p className="p-3 text-sm text-slate-500">
              Aucune conversation. Complétez une formation pour recevoir une rétroaction.
            </p>
          ) : (
            <ul className="space-y-2">
              {conversations.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => openConversation(c.id)}
                    className="w-full rounded-lg border border-slate-200 p-3 text-left transition hover:border-brand hover:bg-slate-50"
                  >
                    <p className="text-sm font-medium text-slate-800">{c.title}</p>
                    <p className="mt-0.5 text-[11px] text-slate-400">
                      {new Date(c.created_at).toLocaleString("fr-CA")}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </>
  );
}
