import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

export default function CookingMode() {
    const { id } = useParams();
    const [r, setR] = useState(null);
    const [step, setStep] = useState(0);

    useEffect(() => { api.get(`/recipes/${id}`).then((res) => setR(res.data)); }, [id]);

    if (!r) return <div className="p-12 cp-kicker">Laden…</div>;
    const total = r.steps.length || 1;

    return (
        <div className="min-h-screen flex flex-col bg-[color:var(--bg)]">
            <header className="flex items-center justify-between px-6 py-4 border-b border-[color:var(--border)] bg-white">
                <div>
                    <div className="cp-kicker">Kochmodus</div>
                    <h1 className="font-display text-xl sm:text-2xl font-bold">{r.title}</h1>
                </div>
                <Link to={`/recipes/${id}`} className="cp-btn-ghost" data-testid="exit-cook-btn">
                    <X className="h-5 w-5" /> Beenden
                </Link>
            </header>

            <div className="flex-1 grid lg:grid-cols-[320px_1fr]">
                <aside className="bg-white border-r border-[color:var(--border)] p-6 hidden lg:block overflow-y-auto">
                    <div className="cp-kicker mb-3">Zutaten</div>
                    <ul className="space-y-2">
                        {r.ingredients.map((ing, i) => (
                            <li key={i} className="flex justify-between border-b border-[color:var(--border)] py-2 text-lg">
                                <span>{ing.name}</span>
                                <span className="text-[color:var(--muted)]">{ing.amount} {ing.unit}</span>
                            </li>
                        ))}
                    </ul>
                </aside>

                <div className="flex flex-col items-center justify-center p-6 sm:p-12">
                    <div className="max-w-3xl w-full text-center">
                        <div className="cp-kicker mb-4">Schritt {step + 1} / {total}</div>
                        <div className="h-2 w-full rounded-full bg-[color:var(--surface-2)] mb-10 overflow-hidden">
                            <div className="h-full bg-[color:var(--primary)] transition-all" style={{ width: `${((step + 1) / total) * 100}%` }} />
                        </div>
                        <p className="font-display text-3xl sm:text-4xl lg:text-5xl leading-snug font-semibold" data-testid="cooking-step-text">
                            {r.steps[step] || "Keine Schritte definiert."}
                        </p>
                    </div>
                </div>
            </div>

            <footer className="border-t border-[color:var(--border)] bg-white p-4 flex gap-4 justify-between">
                <button
                    disabled={step === 0}
                    onClick={() => setStep(step - 1)}
                    className="cp-btn-secondary flex-1 disabled:opacity-40 min-h-[64px]"
                    data-testid="prev-step-btn"
                >
                    <ChevronLeft className="h-6 w-6" /> Zurück
                </button>
                <button
                    disabled={step >= total - 1}
                    onClick={() => setStep(step + 1)}
                    className="cp-btn-primary flex-[2] disabled:opacity-40 min-h-[64px] text-lg"
                    data-testid="next-step-btn"
                >
                    Weiter <ChevronRight className="h-6 w-6" />
                </button>
            </footer>
        </div>
    );
}
