"use client";

import Image from "next/image";
import { UserButton } from "@clerk/nextjs";
import { AppProvider, useApp, type Tab } from "./AppContext";
import DashboardView from "./views/DashboardView";
import CompletedView from "./views/CompletedView";
import SuggestionsView from "./views/SuggestionsView";
import FeedbackView from "./views/FeedbackView";
import LearningView from "./views/LearningView";
import NotificationsView from "./views/NotificationsView";
import TrainingView from "./views/TrainingView";
import ConversationScreen from "./ConversationScreen";
import {
  IconBell,
  IconChat,
  IconCompleted,
  IconDashboard,
  IconLearning,
  IconSuggestions,
} from "./Icons";

const TABS: { key: Tab; label: string; Icon: typeof IconDashboard }[] = [
  { key: "dashboard", label: "Tableau de bord", Icon: IconDashboard },
  { key: "completed", label: "Complétées", Icon: IconCompleted },
  { key: "suggestions", label: "Suggestions", Icon: IconSuggestions },
  { key: "feedback", label: "Agent de rétroaction", Icon: IconChat },
  { key: "learning", label: "Mon apprentissage", Icon: IconLearning },
  { key: "notifications", label: "Notifications", Icon: IconBell },
];

function Shell() {
  const {
    tab,
    setTab,
    selectedTrainingId,
    unread,
    toastMsg,
    openTraining,
    activeConversationId,
  } = useApp();

  return (
    <div className="flex h-screen flex-col bg-[var(--background)] text-slate-800">
      {/* Top bar */}
      <header className="flex h-14 items-center gap-3 border-b border-slate-200 bg-white px-5">
        <Image src="/sensai_logo.png" alt="SENSAI" width={28} height={28} className="rounded" />
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight text-slate-900">SENSAI</div>
          <div className="-mt-0.5 text-[11px] text-slate-400">Rétroaction par concordance</div>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <button
            onClick={() => setTab("notifications")}
            className="relative rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
            title="Notifications"
          >
            <IconBell />
            {unread > 0 && (
              <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                {unread}
              </span>
            )}
          </button>
          <div className="ml-1">
            <UserButton />
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Left nav */}
        <nav className="w-56 shrink-0 border-r border-slate-200 bg-white p-3">
          <ul className="space-y-0.5">
            {TABS.map(({ key, label, Icon }) => {
              const active = tab === key && !selectedTrainingId;
              return (
                <li key={key}>
                  <button
                    onClick={() => {
                      openTraining(null);
                      setTab(key);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                      active ? "bg-brand text-white" : "text-slate-600 hover:bg-slate-100"
                    }`}
                  >
                    <Icon />
                    <span>{label}</span>
                    {key === "notifications" && unread > 0 && (
                      <span className="ml-auto rounded-full bg-red-500 px-1.5 text-[10px] font-bold text-white">
                        {unread}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Content */}
        <main className="thin-scroll min-h-0 flex-1 overflow-y-auto p-8">
          {selectedTrainingId ? (
            <TrainingView userTrainingId={selectedTrainingId} />
          ) : tab === "dashboard" ? (
            <DashboardView />
          ) : tab === "completed" ? (
            <CompletedView />
          ) : tab === "suggestions" ? (
            <SuggestionsView />
          ) : tab === "feedback" ? (
            <FeedbackView />
          ) : tab === "learning" ? (
            <LearningView />
          ) : (
            <NotificationsView />
          )}
        </main>
      </div>

      {activeConversationId && <ConversationScreen conversationId={activeConversationId} />}

      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-[60] flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-3 text-sm text-white shadow-lg">
          <IconBell width={16} height={16} />
          {toastMsg}
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
