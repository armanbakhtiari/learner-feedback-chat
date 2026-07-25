"use client";

import { useApp } from "../AppContext";

const DOT: Record<string, string> = {
  evaluation_ready: "bg-blue-500",
  feedback_ready: "bg-emerald-500",
  suggestions_ready: "bg-violet-500",
  pipeline_error: "bg-red-500",
};

export default function NotificationsView() {
  const { notifications, markRead, setTab, openTraining } = useApp();

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Notifications</h1>
      <p className="mb-6 mt-1 text-sm text-slate-500">Vos évaluations et rétroactions.</p>

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
              <div className="flex items-start gap-3">
                <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${DOT[n.type] || "bg-slate-400"}`} />
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
