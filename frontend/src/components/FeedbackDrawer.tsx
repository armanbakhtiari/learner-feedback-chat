"use client";

import { useEffect, useRef, useState } from "react";
import { useApp } from "./AppContext";
import Markdown from "./Markdown";
import type { Message } from "@/lib/types";

export default function FeedbackDrawer() {
  const { api, drawerOpen, setDrawerOpen, conversations, activeConversationId, openConversation } =
    useApp();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [webSearch, setWebSearch] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeConv = conversations.find((c) => c.id === activeConversationId);

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    let active = true;
    setLoading(true);
    api
      .get<{ messages: Message[] }>(`/conversations/${activeConversationId}/messages`)
      .then((r) => active && setMessages(r.messages))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, activeConversationId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    const text = input.trim();
    if (!text || !activeConversationId || sending) return;
    setInput("");
    setMessages((m) => [
      ...m,
      { id: "tmp-" + Date.now(), role: "user_message", content: text, metadata: {}, created_at: "" },
    ]);
    setSending(true);
    try {
      const r = await api.post<{ response: string }>(
        `/conversations/${activeConversationId}/chat`,
        { message: text, web_search_enabled: webSearch },
      );
      setMessages((m) => [
        ...m,
        {
          id: "resp-" + Date.now(),
          role: "response_message",
          content: r.response,
          metadata: {},
          created_at: "",
        },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          id: "err-" + Date.now(),
          role: "response_message",
          content: "_Une erreur est survenue. Veuillez réessayer._",
          metadata: {},
          created_at: "",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  if (!drawerOpen) return null;

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20" onClick={() => setDrawerOpen(false)} />
      <aside className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-xl">
        <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
          <span className="font-semibold text-slate-800">💬 Rétroactions</span>
          <button
            onClick={() => setDrawerOpen(false)}
            className="ml-auto rounded px-2 py-1 text-slate-500 hover:bg-slate-100"
          >
            ✕
          </button>
        </div>

        {!activeConversationId ? (
          // Conversation list
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
                      className="w-full rounded-lg border border-slate-200 p-3 text-left hover:border-brand hover:bg-slate-50"
                    >
                      <p className="font-medium text-slate-800">{c.title}</p>
                      <p className="text-[11px] text-slate-400">
                        {new Date(c.created_at).toLocaleString("fr-CA")}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          // Chat
          <>
            <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-2">
              <button
                onClick={() => openConversation("")}
                className="text-sm text-slate-500 hover:text-slate-700"
              >
                ← Conversations
              </button>
              <span className="truncate text-sm font-medium text-slate-700">{activeConv?.title}</span>
            </div>

            <div ref={scrollRef} className="thin-scroll flex-1 space-y-3 overflow-y-auto p-4">
              {loading ? (
                <p className="text-sm text-slate-400">Chargement…</p>
              ) : (
                messages.map((m) => (
                  <div
                    key={m.id}
                    className={m.role === "user_message" ? "flex justify-end" : "flex justify-start"}
                  >
                    <div
                      className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-sm ${
                        m.role === "user_message"
                          ? "bg-brand text-white"
                          : "border border-slate-200 bg-slate-50 text-slate-800"
                      }`}
                    >
                      {m.role === "user_message" ? m.content : <Markdown>{m.content}</Markdown>}
                    </div>
                  </div>
                ))
              )}
              {sending && <p className="text-sm text-slate-400">L&apos;agent rédige…</p>}
            </div>

            <div className="border-t border-slate-200 p-3">
              <label className="mb-2 flex items-center gap-1.5 text-xs text-slate-500">
                <input
                  type="checkbox"
                  checked={webSearch}
                  onChange={(e) => setWebSearch(e.target.checked)}
                />
                🌐 Recherche Web
              </label>
              <div className="flex items-end gap-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}
                  rows={2}
                  placeholder="Posez une question sur votre rétroaction…"
                  className="flex-1 resize-none rounded-lg border border-slate-300 p-2.5 text-sm outline-none focus:border-brand"
                />
                <button
                  onClick={send}
                  disabled={sending || !input.trim()}
                  className="rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40"
                >
                  ↑
                </button>
              </div>
            </div>
          </>
        )}
      </aside>
    </>
  );
}
