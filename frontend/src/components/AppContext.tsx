"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useApi } from "@/lib/api";
import { makeSupabase } from "@/lib/supabase";
import type { Conversation, NotificationRow } from "@/lib/types";

export type Tab =
  | "dashboard"
  | "completed"
  | "suggestions"
  | "feedback"
  | "learning"
  | "notifications";

interface AppCtx {
  api: ReturnType<typeof useApi>;
  tab: Tab;
  setTab: (t: Tab) => void;
  selectedTrainingId: string | null;
  openTraining: (id: string | null) => void;
  refreshTick: number;
  bump: () => void;
  notifications: NotificationRow[];
  unread: number;
  markRead: (id: string) => void;
  conversations: Conversation[];
  activeConversationId: string | null;
  openConversation: (id: string) => void;
  closeConversation: () => void;
  toast: (msg: string) => void;
  toastMsg: string | null;
}

const Ctx = createContext<AppCtx | null>(null);
export const useApp = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp outside provider");
  return v;
};

export function AppProvider({ children }: { children: React.ReactNode }) {
  const api = useApi();
  const { getToken, userId } = useAuth();

  const [tab, setTab] = useState<Tab>("dashboard");
  const [selectedTrainingId, setSelectedTrainingId] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [notifications, setNotifications] = useState<NotificationRow[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const bump = useCallback(() => setRefreshTick((t) => t + 1), []);

  const toast = useCallback((msg: string) => {
    setToastMsg(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastMsg(null), 4000);
  }, []);

  const openTraining = useCallback((id: string | null) => setSelectedTrainingId(id), []);

  // Opening a conversation shows it full-screen, over the current tab.
  const openConversation = useCallback((id: string) => setActiveConversationId(id), []);

  const closeConversation = useCallback(() => setActiveConversationId(null), []);

  const refreshNotifications = useCallback(async () => {
    try {
      const r = await api.get<{ notifications: NotificationRow[] }>("/notifications");
      setNotifications(r.notifications);
    } catch {
      /* transient; the 20s poll below retries */
    }
  }, [api]);

  // Unlike notifications there is no poll behind this one, so a failed first load used to
  // leave "Agent de rétroaction" empty until the user refreshed the page by hand.
  const refreshConversations = useCallback(async () => {
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const r = await api.get<{ conversations: Conversation[] }>("/conversations");
        setConversations(r.conversations);
        return;
      } catch {
        await new Promise((res) => setTimeout(res, 400 * (attempt + 1)));
      }
    }
  }, [api]);

  const markRead = useCallback(
    async (id: string) => {
      setNotifications((ns) => ns.map((n) => (n.id === id ? { ...n, read: true } : n)));
      try {
        await api.post(`/notifications/${id}/read`);
      } catch {
        /* ignore */
      }
    },
    [api],
  );

  // Initial load + refetch conversations on every tick.
  useEffect(() => {
    refreshNotifications();
    refreshConversations();
  }, [refreshNotifications, refreshConversations, refreshTick]);

  // Poll fallback (works even if realtime/third-party-auth isn't set up yet).
  useEffect(() => {
    const t = setInterval(() => refreshNotifications(), 20000);
    return () => clearInterval(t);
  }, [refreshNotifications]);

  // Supabase Realtime push on new notifications.
  useEffect(() => {
    if (!userId) return;
    const sb = makeSupabase(getToken);
    const channel = sb
      .channel("notifications-" + userId)
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "notifications", filter: `clerk_user_id=eq.${userId}` },
        (payload) => {
          const n = payload.new as NotificationRow;
          setNotifications((ns) => [n, ...ns]);
          toast(n.title);
          bump(); // refresh dashboard/completed/conversations
        },
      )
      .subscribe();
    return () => {
      sb.removeChannel(channel);
    };
  }, [userId, getToken, toast, bump]);

  const unread = useMemo(() => notifications.filter((n) => !n.read).length, [notifications]);

  const value: AppCtx = {
    api,
    tab,
    setTab,
    selectedTrainingId,
    openTraining,
    refreshTick,
    bump,
    notifications,
    unread,
    markRead,
    conversations,
    activeConversationId,
    openConversation,
    closeConversation,
    toast,
    toastMsg,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
