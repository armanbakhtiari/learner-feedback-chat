"use client";

import Image from "next/image";
import { UserButton } from "@clerk/nextjs";
import { AppProvider, useApp, type Tab } from "./AppContext";
import DashboardView from "./views/DashboardView";
import CompletedView from "./views/CompletedView";
import SuggestionsView from "./views/SuggestionsView";
import LearningView from "./views/LearningView";
import NotificationsView from "./views/NotificationsView";
import TrainingView from "./views/TrainingView";
import FeedbackDrawer from "./FeedbackDrawer";

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "dashboard", label: "Tableau de bord", icon: "🏠" },
  { key: "completed", label: "Complétées", icon: "✅" },
  { key: "suggestions", label: "Suggestions", icon: "🎯" },
  { key: "learning", label: "Mon apprentissage", icon: "📈" },
  { key: "notifications", label: "Notifications", icon: "🔔" },
];

function Shell() {
  const { tab, setTab, selectedTrainingId, unread, setDrawerOpen, toastMsg, openTraining } = useApp();

  return (
    <div className="flex h-screen flex-col bg-[var(--background)]">
      {/* Top bar */}
      <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5">
        <Image src="/sensai_logo.png" alt="SENSAI" width={32} height={32} />
        <span className="font-semibold text-slate-800">SENSAI — Rétroaction</span>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setDrawerOpen(true)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            💬 Rétroactions
          </button>
          <button
            onClick={() => setTab("notifications")}
            className="relative rounded-lg px-2 py-1.5 text-lg hover:bg-slate-100"
            title="Notifications"
          >
            🔔
            {unread > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                {unread}
              </span>
            )}
          </button>
          <UserButton />
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Left nav */}
        <nav className="w-52 shrink-0 border-r border-slate-200 bg-white p-3">
          <ul className="space-y-1">
            {TABS.map((t) => (
              <li key={t.key}>
                <button
                  onClick={() => {
                    openTraining(null);
                    setTab(t.key);
                  }}
                  className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium ${
                    tab === t.key && !selectedTrainingId
                      ? "bg-brand text-white"
                      : "text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <span>{t.icon}</span>
                  <span>{t.label}</span>
                  {t.key === "notifications" && unread > 0 && (
                    <span className="ml-auto rounded-full bg-red-500 px-1.5 text-[10px] font-bold text-white">
                      {unread}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Content */}
        <main className="thin-scroll min-h-0 flex-1 overflow-y-auto p-6">
          {selectedTrainingId ? (
            <TrainingView userTrainingId={selectedTrainingId} />
          ) : tab === "dashboard" ? (
            <DashboardView />
          ) : tab === "completed" ? (
            <CompletedView />
          ) : tab === "suggestions" ? (
            <SuggestionsView />
          ) : tab === "learning" ? (
            <LearningView />
          ) : (
            <NotificationsView />
          )}
        </main>
      </div>

      <FeedbackDrawer />

      {toastMsg && (
        <div className="fixed bottom-5 right-5 z-50 rounded-lg bg-slate-800 px-4 py-3 text-sm text-white shadow-lg">
          🔔 {toastMsg}
        </div>
      )}
    </div>
  );
}

export default function AppShell() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}
