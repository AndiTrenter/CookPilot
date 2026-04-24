import React, { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Send, Sparkles, Plus, Trash2 } from "lucide-react";

const quickPrompts = [
    "Was kann ich heute mit dem machen, was ich da habe?",
    "Schnelles Abendessen in 20 Minuten",
    "Plane mir 5 Gerichte für diese Woche",
    "Erstelle mir eine Einkaufsliste für 4 Personen",
];

export default function Chat() {
    const [sessions, setSessions] = useState([]);
    const [sid, setSid] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [sending, setSending] = useState(false);
    const ref = useRef(null);

    const loadSessions = async () => {
        const { data } = await api.get("/chat/sessions");
        setSessions(data);
    };

    const loadMessages = async (id) => {
        if (!id) return setMessages([]);
        const { data } = await api.get(`/chat/sessions/${id}/messages`);
        setMessages(data);
    };

    useEffect(() => { loadSessions(); }, []);
    useEffect(() => { loadMessages(sid); }, [sid]);
    useEffect(() => { ref.current?.scrollTo({ top: ref.current.scrollHeight }); }, [messages]);

    const send = async (text) => {
        const msg = text ?? input;
        if (!msg.trim() || sending) return;
        setSending(true);
        setMessages((m) => [...m, { id: Math.random().toString(36), role: "user", content: msg, created_at: new Date().toISOString() }]);
        setInput("");
        try {
            const { data } = await api.post("/chat/send", { session_id: sid, message: msg });
            setSid(data.session_id);
            await loadMessages(data.session_id);
            if (!sid) loadSessions();
        } catch (err) {
            const detail = err?.response?.data?.detail || "KI-Fehler";
            toast.error(detail);
            setMessages((m) => [...m, { id: "err", role: "assistant", content: `⚠️ ${detail}`, created_at: new Date().toISOString() }]);
        } finally {
            setSending(false);
        }
    };

    const delSession = async (id) => {
        await api.delete(`/chat/sessions/${id}`);
        if (sid === id) setSid(null);
        loadSessions();
    };

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-6xl mx-auto">
            <div className="mb-6">
                <div className="cp-kicker mb-2">Koch-Chat</div>
                <h1 className="font-display text-4xl sm:text-5xl font-bold">Frag CookPilot</h1>
            </div>

            <div className="grid lg:grid-cols-[260px_1fr] gap-6">
                <aside className="cp-card p-4 h-fit">
                    <button onClick={() => setSid(null)} className="cp-btn-secondary w-full mb-3" data-testid="new-chat-btn">
                        <Plus className="h-4 w-4" /> Neuer Chat
                    </button>
                    <div className="space-y-1 max-h-[50vh] overflow-y-auto">
                        {sessions.map((s) => (
                            <div key={s.id} className={`flex items-center gap-1 rounded-2xl px-3 py-2 cursor-pointer ${sid === s.id ? "bg-[color:var(--surface-2)]" : "hover:bg-[color:var(--surface-2)]"}`}>
                                <div onClick={() => setSid(s.id)} className="flex-1 text-sm truncate" data-testid={`chat-session-${s.id}`}>{s.title}</div>
                                <button onClick={() => delSession(s.id)} className="text-[color:var(--muted)] hover:text-[color:var(--danger)]" data-testid={`chat-del-${s.id}`}>
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        ))}
                        {sessions.length === 0 && <div className="text-xs text-[color:var(--muted)] py-2 px-3">Noch keine Unterhaltung.</div>}
                    </div>
                </aside>

                <section className="cp-card flex flex-col min-h-[60vh]">
                    <div ref={ref} className="flex-1 overflow-y-auto space-y-4 pr-2">
                        {messages.length === 0 && (
                            <div className="text-center py-12">
                                <Sparkles className="h-10 w-10 mx-auto mb-4 text-[color:var(--primary)]" />
                                <p className="text-[color:var(--muted)] mb-6">Was möchtest du heute kochen?</p>
                                <div className="flex flex-wrap justify-center gap-2">
                                    {quickPrompts.map((q) => (
                                        <button key={q} onClick={() => send(q)} className="cp-chip hover:border-[color:var(--primary)]" data-testid={`quick-prompt-${q.slice(0,10)}`}>
                                            {q}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                        {messages.map((m) => (
                            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                                <div className={`max-w-[80%] rounded-3xl px-5 py-3 text-base whitespace-pre-wrap ${m.role === "user" ? "bg-[color:var(--primary)] text-white" : "bg-[color:var(--surface-2)] text-[color:var(--text)]"}`}>
                                    {m.content}
                                </div>
                            </div>
                        ))}
                        {sending && <div className="text-sm text-[color:var(--muted)] italic">CookPilot denkt nach…</div>}
                    </div>

                    <form
                        onSubmit={(e) => { e.preventDefault(); send(); }}
                        className="flex gap-2 mt-4 pt-4 border-t border-[color:var(--border)]"
                    >
                        <input
                            className="cp-input flex-1"
                            placeholder="Frag nach Rezepten, Wochenplänen…"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            disabled={sending}
                            data-testid="chat-input"
                        />
                        <button className="cp-btn-primary" disabled={sending} data-testid="chat-send-btn">
                            <Send className="h-5 w-5" />
                        </button>
                    </form>
                </section>
            </div>
        </div>
    );
}
