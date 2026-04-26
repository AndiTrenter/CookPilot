import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Sparkles, Loader2, Clock, ChefHat } from "lucide-react";

export default function SuggestionWidget() {
    const [hint, setHint] = useState("");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    const ask = async () => {
        setLoading(true);
        try {
            const { data } = await api.post("/recipes/suggestions", { hint, max_results: 3 });
            setResult(data);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Vorschläge fehlgeschlagen");
        } finally {
            setLoading(false);
        }
    };

    return (
        <section className="cp-card">
            <div className="flex items-center justify-between mb-5">
                <h2 className="font-display text-2xl font-bold flex items-center gap-2">
                    <Sparkles className="h-6 w-6 text-[color:var(--primary)]" /> Was kann ich heute kochen?
                </h2>
            </div>
            <div className="flex gap-2 mb-4">
                <input
                    className="cp-input flex-1"
                    placeholder="Optional: schnelles Abendessen, leicht, vegetarisch…"
                    value={hint}
                    onChange={(e) => setHint(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && ask()}
                    data-testid="suggest-hint-input"
                />
                <button onClick={ask} disabled={loading} className="cp-btn-primary" data-testid="suggest-btn">
                    {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Sparkles className="h-5 w-5" />}
                    Vorschlagen
                </button>
            </div>

            {result && (
                <div className="space-y-3 mt-4 animate-fade-in">
                    {result.reasoning && (
                        <p className="text-sm text-[color:var(--muted)] italic">{result.reasoning}</p>
                    )}
                    {result.suggestions.length === 0 ? (
                        <div className="text-[color:var(--muted)] text-sm py-3">Aktuell keine passenden Rezepte aus deiner Sammlung. Importiere ein paar weitere oder ändere die Vorgabe.</div>
                    ) : (
                        result.suggestions.map((s) => (
                            <Link key={s.recipe_id} to={`/recipes/${s.recipe_id}`} className="cp-tile flex flex-col sm:flex-row gap-4 hover:border-[color:var(--primary)]" data-testid={`suggest-result-${s.recipe_id}`}>
                                {s.image_url ? (
                                    <img src={s.image_url} alt="" className="w-full sm:w-32 h-32 sm:h-24 object-cover rounded-2xl" />
                                ) : (
                                    <div className="w-full sm:w-32 h-32 sm:h-24 rounded-2xl bg-[color:var(--surface-2)] flex items-center justify-center">
                                        <ChefHat className="h-8 w-8 text-[color:var(--muted)]" />
                                    </div>
                                )}
                                <div className="flex-1 min-w-0">
                                    <div className="font-display text-lg font-bold">{s.title}</div>
                                    <div className="flex flex-wrap gap-2 mt-1">
                                        {s.category && <span className="cp-chip">{s.category}</span>}
                                        {s.cook_time_min && <span className="cp-chip"><Clock className="h-3 w-3 mr-1" /> {s.cook_time_min} Min</span>}
                                    </div>
                                    {s.reason && <p className="text-sm text-[color:var(--muted)] mt-2">{s.reason}</p>}
                                    {s.missing_ingredients && s.missing_ingredients.length > 0 && (
                                        <p className="text-xs text-[color:var(--warning)] mt-2">
                                            Noch fehlt: {s.missing_ingredients.join(", ")}
                                        </p>
                                    )}
                                </div>
                            </Link>
                        ))
                    )}
                </div>
            )}
        </section>
    );
}
