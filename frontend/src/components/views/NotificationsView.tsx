"use client";

import { useApp } from "../AppContext";

const ICONS: Record<string, string> = {
  evaluation_ready: "📊",
  feedback_ready: "💬",
  suggestions_ready: "🎯",
  pipeline_error: "⚠️",
};

export default function NotificationsView() {
  const { notifications, markRead, setTab, openTraining } = useApp();

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 text-2xl font-bold text-slate-800">Notifications</h1>
      <p className="mb-5 text-sm text-slate-500">Vos évaluations et rétroactions.</p>

      {notifications.length === 0 ? (
        <p className="text-slate-500">Aucune notification.</p>
      ) : (
        <ul className="space-y-2">
          {notifications.map((n) => (
            <li
              key={n.id}
              onClick={() => {
                if (!n.read) markRead(n.id);
                if (n.type === "feedback_ready" || n.type === "evaluation_ready") {
                  openTraining(null);
                  setTab("completed");
                }
              }}
              className={`cursor-pointer rounded-lg border p-3 ${
                n.read ? "border-slate-200 bg-white" : "border-brand/40 bg-blue-50"
              }`}
            >
              <div className="flex items-start gap-2">
                <span className="text-lg">{ICONS[n.type] || "🔔"}</span>
                <div className="min-w-0">
                  <p className="font-medium text-slate-800">{n.title}</p>
                  {n.body && <p className="text-sm text-slate-600">{n.body}</p>}
                  <p className="mt-0.5 text-[11px] text-slate-400">
                    {new Date(n.created_at).toLocaleString("fr-CA")}
                  </p>
                </div>
                {!n.read && <span className="ml-auto mt-1 h-2 w-2 shrink-0 rounded-full bg-brand" />}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
