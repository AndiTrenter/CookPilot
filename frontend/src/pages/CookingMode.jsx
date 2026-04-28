import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { ChevronLeft, ChevronRight, X, Minus, Plus } from "lucide-react";

function formatAmount(value) {
    if (!value || value <= 0) return "";
    if (value < 0.05) return "<0.1";
    // Drop trailing zeros: 250 -> "250", 250.5 -> "250.5", 0.7 -> "0.7"
    const rounded = Math.round(value * 10) / 10;
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

export default function CookingMode() {
    const { id } = useParams();
    const [r, setR] = useState(null);
    const [step, setStep] = useState(0);
    const [servings, setServings] = useState(0);

    useEffect(() => {
        api.get(`/recipes/${id}`).then((res) => {
            setR(res.data);
            setServings(res.data.servings || 2);
        });
    }, [id]);

    if (!r) return <div className="p-12 cp-kicker">Laden…</div>;
    const total = r.steps.length || 1;
    const baseServings = Math.max(1, r.servings || 1);
    const factor = servings / baseServings;

    return (
        <div className="min-h-screen flex flex-col">
            <header className="flex items-center justify-between px-6 py-4 border-b border-[color:var(--border)] bg-white/80 backdrop-blur">
                <div>
                    <div className="cp-kicker">Kochmodus</div>
                    <h1 className="font-display text-xl sm:text-2xl font-bold">{r.title}</h1>
                </div>
                <Link to={`/recipes/${id}`} className="cp-btn-ghost" data-testid="exit-cook-btn">
                    <X className="h-5 w-5" /> Beenden
                </Link>
            </header>

            <div className="flex-1 grid lg:grid-cols-[340px_1fr]">
                <aside className="bg-white/85 backdrop-blur border-r border-[color:var(--border)] p-6 hidden lg:flex lg:flex-col overflow-y-auto">
                    <div className="cp-kicker mb-3">Portionen</div>
                    <div className="flex items-center gap-3 mb-6" data-testid="cook-servings-control">
                        <button
                            onClick={() => setServings((s) => Math.max(1, s - 1))}
                            className="cp-btn-secondary h-12 w-12 p-0 shrink-0"
                            data-testid="cook-servings-minus"
                            aria-label="Weniger Portionen"
                        >
                            <Minus className="h-5 w-5" />
                        </button>
                        <input
                            type="number"
                            min={1}
                            max={99}
                            value={servings}
                            onChange={(e) => setServings(Math.max(1, Math.min(99, +e.target.value || 1)))}
                            className="cp-input text-center font-display text-2xl font-bold"
                            data-testid="cook-servings-input"
                        />
                        <button
                            onClick={() => setServings((s) => Math.min(99, s + 1))}
                            className="cp-btn-secondary h-12 w-12 p-0 shrink-0"
                            data-testid="cook-servings-plus"
                            aria-label="Mehr Portionen"
                        >
                            <Plus className="h-5 w-5" />
                        </button>
                    </div>
                    {servings !== baseServings && (
                        <div className="text-xs text-[color:var(--muted)] -mt-3 mb-4" data-testid="cook-servings-hint">
                            Original-Rezept: {baseServings} Portion{baseServings === 1 ? "" : "en"} · Faktor ×{factor.toFixed(2)}
                        </div>
                    )}

                    <div className="cp-kicker mb-3">Zutaten</div>
                    <ul className="space-y-2">
                        {r.ingredients.map((ing, i) => {
                            const scaled = (ing.amount || 0) * factor;
                            return (
                                <li key={i} className="flex justify-between border-b border-[color:var(--border)] py-2 text-lg" data-testid={`cook-ing-${i}`}>
                                    <span>{ing.name}</span>
                                    <span className="text-[color:var(--muted)] font-semibold">
                                        {formatAmount(scaled)} {ing.unit}
                                    </span>
                                </li>
                            );
                        })}
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

            <footer className="border-t border-[color:var(--border)] bg-white/85 backdrop-blur p-4 flex gap-4 justify-between">
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
