import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";
import { ChefHat } from "lucide-react";

export default function AcceptInvite() {
    const { token } = useParams();
    const nav = useNavigate();
    const { setUser } = useAuth();
    const [state, setState] = useState({ loading: true, email: "", role: "" });
    const [form, setForm] = useState({ name: "", password: "", password2: "" });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        api.get(`/auth/invite/${token}`)
            .then((res) => setState({ loading: false, email: res.data.email, role: res.data.role }))
            .catch((err) => {
                toast.error(err?.response?.data?.detail || "Einladung ungültig");
                setState({ loading: false, email: "", role: "" });
            });
    }, [token]);

    const submit = async (e) => {
        e.preventDefault();
        if (form.password.length < 8) {
            toast.error("Mindestens 8 Zeichen");
            return;
        }
        if (form.password !== form.password2) {
            toast.error("Passwörter stimmen nicht überein");
            return;
        }
        setSubmitting(true);
        try {
            const { data } = await api.post("/auth/accept-invite", {
                token,
                name: form.name,
                password: form.password,
            });
            localStorage.setItem("cp_token", data.token);
            localStorage.setItem("cp_user", JSON.stringify(data.user));
            setUser(data.user);
            toast.success("Konto erstellt - willkommen!");
            nav("/");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Fehler");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            <div className="w-full max-w-md">
                <div className="flex items-center gap-3 mb-10">
                    <div className="h-12 w-12 rounded-2xl flex items-center justify-center bg-[color:var(--primary)] text-white">
                        <ChefHat className="h-6 w-6" strokeWidth={2.5} />
                    </div>
                    <div className="font-display text-3xl font-bold">CookPilot</div>
                </div>
                <div className="cp-card">
                    <h1 className="font-display text-3xl font-bold mb-2">Konto erstellen</h1>
                    {state.loading ? (
                        <p className="text-[color:var(--muted)]">Einladung wird geprüft…</p>
                    ) : state.email ? (
                        <>
                            <p className="text-[color:var(--muted)] mb-8">Einladung gültig für <strong>{state.email}</strong> · Rolle: {state.role}</p>
                            <form onSubmit={submit} className="space-y-5">
                                <div>
                                    <label className="cp-label">Name</label>
                                    <input className="cp-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required data-testid="invite-name-input" />
                                </div>
                                <div>
                                    <label className="cp-label">Passwort</label>
                                    <input type="password" className="cp-input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required data-testid="invite-password-input" />
                                </div>
                                <div>
                                    <label className="cp-label">Passwort bestätigen</label>
                                    <input type="password" className="cp-input" value={form.password2} onChange={(e) => setForm({ ...form, password2: e.target.value })} required data-testid="invite-password2-input" />
                                </div>
                                <button disabled={submitting} className="cp-btn-primary w-full" data-testid="invite-submit-btn">
                                    {submitting ? "Anlegen…" : "Konto erstellen"}
                                </button>
                            </form>
                        </>
                    ) : (
                        <div className="text-[color:var(--danger)] font-semibold">Einladung ungültig oder abgelaufen.</div>
                    )}
                </div>
            </div>
        </div>
    );
}
