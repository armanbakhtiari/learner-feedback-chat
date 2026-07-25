"use client";

import { useEffect, useRef, useState } from "react";
import { useApp } from "./AppContext";
import Markdown from "./Markdown";
import { IconArrowLeft, IconSend } from "./Icons";
import type { Message } from "@/lib/types";

export default function ConversationScreen({ conversationId }: { conversationId: string }) {
  const { api, conversations, closeConversation } = useApp();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [webSearch, setWebSearch] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const conv = conversations.find((c) => c.id === conversationId);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .get<{ messages: Message[] }>(`/conversations/${conversationId}/messages`)
      .then((r) => active && setMessages(r.messages))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, conversationId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending, loading]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setMessages((m) => [
      ...m,
      { id: "tmp-" + Date.now(), role: "user_message", content: text, metadata: {}, created_at: "" },
    ]);
    setSending(true);
    try {
      const r = await api.post<{ response: string }>(`/conversations/${conversationId}/chat`, {
        message: text,
        web_search_enabled: webSearch,
      });
      setMessages((m) => [
        ...m,
        { id: "r-" + Date.now(), role: "response_message", content: r.response, metadata: {}, created_at: "" },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          id: "e-" + Date.now(),
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

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white">
      {/* Header */}
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 px-5">
        <button
          onClick={closeConversation}
          className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
        >
          <IconArrowLeft />
          Retour
        </button>
        <h2 className="truncate text-sm font-semibold text-slate-800">{conv?.title || "Rétroaction"}</h2>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="thin-scroll min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-8">
          {loading ? (
            <p className="text-sm text-slate-400">Chargement…</p>
          ) : (
            <div className="space-y-5">
              {messages.map((m) =>
                m.role === "user_message" ? (
                  <div key={m.id} className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl bg-brand px-4 py-2.5 text-sm text-white">
                      {m.content}
                    </div>
                  </div>
                ) : (
                  <div key={m.id} className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4">
                    <Markdown>{m.content}</Markdown>
                  </div>
                ),
              )}
              {sending && <p className="text-sm text-slate-400">L&apos;agent rédige…</p>}
            </div>
          )}
        </div>
      </div>

      {/* Composer */}
      <div className="shrink-0 border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-3xl px-6 py-4">
          <label className="mb-2 flex items-center gap-2 text-xs text-slate-500">
            <input type="checkbox" checked={webSearch} onChange={(e) => setWebSearch(e.target.checked)} />
            Recherche Web
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
              className="flex-1 resize-none rounded-lg border border-slate-300 p-3 text-sm outline-none focus:border-brand"
            />
            <button
              onClick={send}
              disabled={sending || !input.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-brand px-4 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
            >
              <IconSend />
              Envoyer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
