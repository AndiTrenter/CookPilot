import React, { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";
import { ChefHat } from "lucide-react";

export default function Login() {
    const { login } = useAuth();
    const nav = useNavigate();
    const loc = useLocation();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);

    const from = loc.state?.from || "/";

    const submit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await login(email, password);
            toast.success("Willkommen zurück");
            nav(from, { replace: true });
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Login fehlgeschlagen");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            <div className="w-full max-w-md">
                <div className="flex items-center gap-3 mb-10">
                    <div className="h-12 w-12 rounded-2xl flex items-center justify-center bg-[color:var(--primary)] text-white">
                        <ChefHat className="h-6 w-6" strokeWidth={2.5} />
                    </div>
                    <div>
                        <div className="font-display text-3xl font-bold">CookPilot</div>
                        <div className="cp-kicker text-[10px]">Dein Küchen-Assistent</div>
                    </div>
                </div>

                <div className="cp-card animate-fade-in">
                    <h1 className="font-display text-3xl sm:text-4xl font-bold mb-2">Anmelden</h1>
                    <p className="text-[color:var(--muted)] mb-8">Melde dich an, um deine Rezepte, Einkaufsliste und Vorräte zu verwalten.</p>

                    <form onSubmit={submit} className="space-y-5">
                        <div>
                            <label className="cp-label" htmlFor="email">E-Mail</label>
                            <input
                                id="email"
                                type="email"
                                className="cp-input"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                data-testid="login-email-input"
                                autoComplete="email"
                            />
                        </div>
                        <div>
                            <label className="cp-label" htmlFor="password">Passwort</label>
                            <input
                                id="password"
                                type="password"
                                className="cp-input"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                data-testid="login-password-input"
                                autoComplete="current-password"
                            />
                        </div>
                        <button type="submit" disabled={loading} className="cp-btn-primary w-full" data-testid="login-submit-btn">
                            {loading ? "Anmelden…" : "Anmelden"}
                        </button>
                    </form>

                    <div className="mt-8 text-xs text-[color:var(--muted)]">
                        Du hast keinen Account? Bitte lasse dich von einem Admin per E-Mail einladen.
                    </div>
                </div>

                <div className="text-center mt-6 text-xs text-[color:var(--muted)]">
                    CookPilot v0.1.0 · Hergestellt für Unraid.
                </div>
            </div>
        </div>
    );
}
