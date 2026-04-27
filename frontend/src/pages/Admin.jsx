import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Copy, Check, X, Eye, EyeOff, ArrowUp, ArrowDown } from "lucide-react";

const TABS = [
    { id: "users", label: "Benutzer" },
    { id: "invites", label: "Einladungen" },
    { id: "ai", label: "KI" },
    { id: "smtp", label: "E-Mail (SMTP)" },
    { id: "aria", label: "Aria" },
    { id: "widgets-dashboard", label: "Widgets Dashboard" },
    { id: "widgets-tablet", label: "Widgets Tablet" },
];

export default function Admin() {
    const [tab, setTab] = useState("users");
    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-6xl mx-auto">
            <div className="mb-6">
                <div className="cp-kicker mb-2">Administration</div>
                <h1 className="font-display text-4xl sm:text-5xl font-bold">Admin</h1>
            </div>
            <div className="flex flex-wrap gap-2 mb-8 border-b border-[color:var(--border)] pb-2">
                {TABS.map((t) => (
                    <button
                        key={t.id}
                        onClick={() => setTab(t.id)}
                        data-testid={`admin-tab-${t.id}`}
                        className={`px-4 py-2 rounded-xl font-semibold text-sm transition-colors ${tab === t.id ? "bg-[color:var(--primary)] text-white" : "hover:bg-[color:var(--surface-2)]"}`}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {tab === "users" && <UsersTab />}
            {tab === "invites" && <InvitesTab />}
            {tab === "ai" && <AiTab />}
            {tab === "smtp" && <SmtpTab />}
            {tab === "aria" && <AriaTab />}
            {tab === "widgets-dashboard" && <WidgetsTab view="dashboard" />}
            {tab === "widgets-tablet" && <WidgetsTab view="tablet" />}
        </div>
    );
}

function UsersTab() {
    const [users, setUsers] = useState([]);
    const load = () => api.get("/users").then((r) => setUsers(r.data));
    useEffect(() => { load(); }, []);
    const update = async (id, patch) => {
        await api.patch(`/users/${id}`, patch);
        load();
    };
    const del = async (id) => {
        if (!window.confirm("Benutzer löschen?")) return;
        await api.delete(`/users/${id}`);
        load();
    };
    return (
        <div className="cp-card">
            <h2 className="font-display text-2xl font-bold mb-5">Benutzer</h2>
            <table className="w-full">
                <thead>
                    <tr className="text-left text-xs uppercase tracking-wider text-[color:var(--muted)]">
                        <th className="py-2">Name</th><th>E-Mail</th><th>Rolle</th><th>Aktiv</th><th>Allergien</th><th></th>
                    </tr>
                </thead>
                <tbody>
                    {users.map((u) => (
                        <tr key={u.id} className="border-t border-[color:var(--border)]">
                            <td className="py-3 font-semibold">{u.name}</td>
                            <td>{u.email}</td>
                            <td>
                                <select value={u.role} onChange={(e) => update(u.id, { role: e.target.value })} className="cp-input py-1" data-testid={`user-role-${u.id}`}>
                                    <option value="user">user</option>
                                    <option value="admin">admin</option>
                                </select>
                            </td>
                            <td>
                                <button onClick={() => update(u.id, { active: !u.active })} data-testid={`user-active-${u.id}`}>
                                    {u.active ? <Check className="h-5 w-5 text-[color:var(--success)]" /> : <X className="h-5 w-5 text-[color:var(--danger)]" />}
                                </button>
                            </td>
                            <td className="text-sm text-[color:var(--muted)]">{(u.allergies || []).join(", ") || "—"}</td>
                            <td>
                                <button onClick={() => del(u.id)} className="cp-btn-ghost text-[color:var(--danger)]" data-testid={`user-del-${u.id}`}><Trash2 className="h-4 w-4" /></button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function InvitesTab() {
    const [list, setList] = useState([]);
    const [email, setEmail] = useState("");
    const [role, setRole] = useState("user");
    const [lastInvite, setLastInvite] = useState(null);
    const load = () => api.get("/invites").then((r) => setList(r.data));
    useEffect(() => { load(); }, []);
    const create = async (e) => {
        e.preventDefault();
        try {
            const { data } = await api.post("/invites", { email, role });
            setLastInvite({ email, url: data.invite_url, mailed: data.email_sent });
            toast.success(data.email_sent ? "Einladung per E-Mail verschickt" : "Einladung erstellt - Link manuell teilen");
            setEmail("");
            load();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Fehler");
        }
    };
    const copyLink = async (token) => {
        const url = `${window.location.origin}/invite/${token}`;
        await navigator.clipboard.writeText(url);
        toast.success("Link kopiert");
    };
    const copyShown = async (url) => {
        await navigator.clipboard.writeText(url);
        toast.success("Link kopiert");
    };
    const del = async (id) => { await api.delete(`/invites/${id}`); load(); };

    return (
        <div className="space-y-6">
            <form onSubmit={create} className="cp-card">
                <h2 className="font-display text-2xl font-bold mb-4">Benutzer einladen</h2>
                <div className="grid grid-cols-12 gap-3">
                    <input type="email" className="cp-input col-span-7" placeholder="E-Mail" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="invite-email-input" />
                    <select value={role} onChange={(e) => setRole(e.target.value)} className="cp-input col-span-3" data-testid="invite-role-select">
                        <option value="user">user</option>
                        <option value="admin">admin</option>
                    </select>
                    <button className="cp-btn-primary col-span-2" data-testid="invite-create-btn">Einladen</button>
                </div>
                {lastInvite && (
                    <div className="mt-5 rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-4" data-testid="invite-last-link-box">
                        <div className="cp-kicker mb-2">
                            Einladung für {lastInvite.email} {lastInvite.mailed ? "(per E-Mail verschickt)" : "(SMTP nicht aktiv - Link manuell weitergeben)"}
                        </div>
                        <div className="flex items-center gap-2">
                            <code className="flex-1 text-xs sm:text-sm break-all bg-white border border-[color:var(--border)] rounded-xl px-3 py-2" data-testid="invite-last-link-url">{lastInvite.url}</code>
                            <button type="button" onClick={() => copyShown(lastInvite.url)} className="cp-btn-secondary" data-testid="invite-last-link-copy">
                                <Copy className="h-4 w-4" /> Kopieren
                            </button>
                        </div>
                        <p className="text-xs text-[color:var(--muted)] mt-2">
                            Tipp: Falls dieser Link nach <code>localhost</code> oder <code>IP</code> aussieht, setze die Umgebungsvariable <code>COOKPILOT_PUBLIC_URL</code> in deiner <code>.env</code> auf die echte Adresse (z.B. <code>http://192.168.1.10:8010</code>) und starte den Container neu.
                        </p>
                    </div>
                )}
            </form>
            <div className="cp-card">
                <h2 className="font-display text-2xl font-bold mb-4">Offene Einladungen</h2>
                {list.length === 0 ? (
                    <div className="text-[color:var(--muted)]">Keine offenen Einladungen.</div>
                ) : (
                    <table className="w-full">
                        <thead><tr className="text-left text-xs uppercase tracking-wider text-[color:var(--muted)]"><th className="py-2">E-Mail</th><th>Rolle</th><th>Status</th><th>Läuft ab</th><th></th></tr></thead>
                        <tbody>
                            {list.map((i) => (
                                <tr key={i.id} className="border-t border-[color:var(--border)]">
                                    <td className="py-3">{i.email}</td>
                                    <td>{i.role}</td>
                                    <td>{i.accepted ? <span className="cp-chip cp-chip-ok">akzeptiert</span> : <span className="cp-chip">offen</span>}</td>
                                    <td className="text-sm text-[color:var(--muted)]">{new Date(i.expires_at).toLocaleDateString("de-DE")}</td>
                                    <td className="flex gap-2 py-3">
                                        {!i.accepted && (
                                            <button onClick={() => copyLink(i.token)} className="cp-btn-ghost" data-testid={`invite-copy-${i.id}`}><Copy className="h-4 w-4" /></button>
                                        )}
                                        <button onClick={() => del(i.id)} className="cp-btn-ghost text-[color:var(--danger)]" data-testid={`invite-del-${i.id}`}><Trash2 className="h-4 w-4" /></button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}

function AiTab() {
    const [s, setS] = useState(null);
    const [show, setShow] = useState(false);
    const [form, setForm] = useState({ openai_api_key: "", openai_model: "gpt-5.2", vision_model: "gpt-4o" });
    useEffect(() => {
        api.get("/settings").then((r) => {
            setS(r.data);
            setForm({ openai_api_key: "", openai_model: r.data.openai_model, vision_model: r.data.vision_model || "gpt-4o" });
        });
    }, []);
    const save = async (e) => {
        e.preventDefault();
        const patch = { openai_model: form.openai_model, vision_model: form.vision_model };
        if (form.openai_api_key) patch.openai_api_key = form.openai_api_key;
        const { data } = await api.put("/settings", patch);
        setS(data);
        setForm({ openai_api_key: "", openai_model: data.openai_model, vision_model: data.vision_model || "gpt-4o" });
        toast.success("Gespeichert");
    };
    if (!s) return null;
    return (
        <form onSubmit={save} className="cp-card space-y-5">
            <h2 className="font-display text-2xl font-bold">OpenAI</h2>
            <p className="text-[color:var(--muted)]">Status: {s.openai_api_key_set ? <span className="cp-chip cp-chip-ok">konfiguriert</span> : <span className="cp-chip cp-chip-warn">nicht konfiguriert</span>}</p>
            <div>
                <label className="cp-label">API-Key (wird nicht zurückgegeben)</label>
                <div className="relative">
                    <input type={show ? "text" : "password"} className="cp-input pr-12" placeholder="sk-…" value={form.openai_api_key} onChange={(e) => setForm({ ...form, openai_api_key: e.target.value })} data-testid="admin-openai-key-input" />
                    <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[color:var(--muted)]">
                        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
                <div>
                    <label className="cp-label">Chat-Modell</label>
                    <input className="cp-input" value={form.openai_model} onChange={(e) => setForm({ ...form, openai_model: e.target.value })} data-testid="admin-openai-model-input" />
                    <p className="text-xs text-[color:var(--muted)] mt-2">Standard: <code>gpt-5.2</code>.</p>
                </div>
                <div>
                    <label className="cp-label">Vision-Modell</label>
                    <input className="cp-input" value={form.vision_model} onChange={(e) => setForm({ ...form, vision_model: e.target.value })} data-testid="admin-vision-model-input" />
                    <p className="text-xs text-[color:var(--muted)] mt-2">Standard: <code>gpt-4o</code> (für Foto-Erkennung und Kassenzettel).</p>
                </div>
            </div>
            <button className="cp-btn-primary" data-testid="admin-openai-save-btn">Speichern</button>
        </form>
    );
}

function SmtpTab() {
    const [s, setS] = useState(null);
    const [form, setForm] = useState({ smtp_host: "", smtp_port: 587, smtp_user: "", smtp_password: "", smtp_from: "", smtp_use_tls: true });
    useEffect(() => {
        api.get("/settings").then((r) => {
            setS(r.data);
            setForm({ smtp_host: r.data.smtp_host, smtp_port: r.data.smtp_port, smtp_user: r.data.smtp_user, smtp_password: "", smtp_from: r.data.smtp_from, smtp_use_tls: r.data.smtp_use_tls });
        });
    }, []);
    const save = async (e) => {
        e.preventDefault();
        const patch = { ...form };
        if (!patch.smtp_password) delete patch.smtp_password;
        const { data } = await api.put("/settings", patch);
        setS(data);
        toast.success("Gespeichert");
    };
    if (!s) return null;
    return (
        <form onSubmit={save} className="cp-card space-y-5">
            <h2 className="font-display text-2xl font-bold">SMTP (E-Mail)</h2>
            <div className="grid grid-cols-2 gap-4">
                <div><label className="cp-label">Host</label><input className="cp-input" value={form.smtp_host} onChange={(e) => setForm({ ...form, smtp_host: e.target.value })} data-testid="admin-smtp-host-input" /></div>
                <div><label className="cp-label">Port</label><input type="number" className="cp-input" value={form.smtp_port} onChange={(e) => setForm({ ...form, smtp_port: +e.target.value })} data-testid="admin-smtp-port-input" /></div>
                <div><label className="cp-label">Benutzer</label><input className="cp-input" value={form.smtp_user} onChange={(e) => setForm({ ...form, smtp_user: e.target.value })} data-testid="admin-smtp-user-input" /></div>
                <div><label className="cp-label">Passwort {s.smtp_password_set && <span className="ml-2 cp-chip cp-chip-ok">gesetzt</span>}</label><input type="password" className="cp-input" placeholder="(leer lassen = unverändert)" value={form.smtp_password} onChange={(e) => setForm({ ...form, smtp_password: e.target.value })} data-testid="admin-smtp-pass-input" /></div>
                <div><label className="cp-label">Absender</label><input className="cp-input" value={form.smtp_from} onChange={(e) => setForm({ ...form, smtp_from: e.target.value })} data-testid="admin-smtp-from-input" /></div>
                <div className="flex items-end gap-2">
                    <input type="checkbox" id="tls" checked={form.smtp_use_tls} onChange={(e) => setForm({ ...form, smtp_use_tls: e.target.checked })} data-testid="admin-smtp-tls-input" />
                    <label htmlFor="tls" className="cp-label">STARTTLS</label>
                </div>
            </div>
            <button className="cp-btn-primary" data-testid="admin-smtp-save-btn">Speichern</button>
        </form>
    );
}

function AriaTab() {
    const [s, setS] = useState(null);
    const [form, setForm] = useState({ aria_shared_secret: "" });
    useEffect(() => { api.get("/settings").then((r) => setS(r.data)); }, []);
    const save = async (e) => {
        e.preventDefault();
        const { data } = await api.put("/settings", form);
        setS(data);
        setForm({ aria_shared_secret: "" });
        toast.success("Gespeichert");
    };
    if (!s) return null;
    return (
        <form onSubmit={save} className="cp-card space-y-5">
            <h2 className="font-display text-2xl font-bold">Aria-Integration</h2>
            <p className="text-[color:var(--muted)]">Status Shared Secret: {s.aria_shared_secret_set ? <span className="cp-chip cp-chip-ok">konfiguriert</span> : <span className="cp-chip cp-chip-warn">nicht konfiguriert</span>}</p>
            <div>
                <label className="cp-label">Shared Secret</label>
                <input className="cp-input" placeholder="(leer lassen = unverändert)" value={form.aria_shared_secret} onChange={(e) => setForm({ aria_shared_secret: e.target.value })} data-testid="admin-aria-secret-input" />
                <p className="text-xs text-[color:var(--muted)] mt-2">Wird in Aria hinterlegt. Aria nutzt <code>POST /api/aria/sso</code> sowie <code>GET /api/aria/purchases/aggregate</code>.</p>
            </div>
            <button className="cp-btn-primary" data-testid="admin-aria-save-btn">Speichern</button>
        </form>
    );
}

function WidgetsTab({ view }) {
    const [catalog, setCatalog] = useState([]);
    const [list, setList] = useState([]);

    const load = async () => {
        const [cat, cur] = await Promise.all([
            api.get("/widgets/catalog").then((r) => r.data),
            api.get(`/widgets/${view}`).then((r) => r.data),
        ]);
        setCatalog(cat.filter((c) => c.views.includes(view)));
        setList(cur.map((c) => ({ widget: c.widget, visible: c.visible !== false })));
    };
    useEffect(() => { load(); }, [view]);

    const move = (i, dir) => {
        const arr = [...list];
        const j = i + dir;
        if (j < 0 || j >= arr.length) return;
        [arr[i], arr[j]] = [arr[j], arr[i]];
        setList(arr);
    };
    const toggleVisible = (i) => {
        const arr = [...list];
        arr[i] = { ...arr[i], visible: !arr[i].visible };
        setList(arr);
    };
    const addWidget = (key) => {
        if (list.find((l) => l.widget === key)) return toast.error("Bereits hinzugefügt");
        setList([...list, { widget: key, visible: true }]);
    };
    const removeWidget = (i) => setList(list.filter((_, idx) => idx !== i));

    const save = async () => {
        await api.put(`/widgets/${view}`, { widgets: list });
        toast.success("Widget-Layout gespeichert");
    };

    return (
        <div className="space-y-6">
            <div className="cp-card">
                <h2 className="font-display text-2xl font-bold mb-5">Widgets - {view === "tablet" ? "Küchen-Tablet" : "Dashboard"}</h2>
                <div className="space-y-2">
                    {list.map((w, i) => {
                        const meta = catalog.find((c) => c.key === w.widget);
                        return (
                            <div key={w.widget + i} className="flex items-center gap-2 rounded-2xl border border-[color:var(--border)] p-3" data-testid={`widget-row-${w.widget}`}>
                                <div className="flex-1 font-semibold">{meta?.label || w.widget}</div>
                                <button onClick={() => move(i, -1)} className="cp-btn-ghost"><ArrowUp className="h-4 w-4" /></button>
                                <button onClick={() => move(i, 1)} className="cp-btn-ghost"><ArrowDown className="h-4 w-4" /></button>
                                <button onClick={() => toggleVisible(i)} className="cp-btn-ghost">{w.visible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4 opacity-50" />}</button>
                                <button onClick={() => removeWidget(i)} className="cp-btn-ghost text-[color:var(--danger)]"><Trash2 className="h-4 w-4" /></button>
                            </div>
                        );
                    })}
                </div>
                <button onClick={save} className="cp-btn-primary mt-5" data-testid={`widgets-save-${view}`}>Speichern</button>
            </div>
            <div className="cp-card">
                <h3 className="cp-kicker mb-3">Verfügbare Widgets</h3>
                <div className="flex flex-wrap gap-2">
                    {catalog.map((c) => (
                        <button key={c.key} onClick={() => addWidget(c.key)} className="cp-chip hover:border-[color:var(--primary)]" data-testid={`widget-add-${c.key}`}>
                            <Plus className="h-3 w-3 mr-1" /> {c.label}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
