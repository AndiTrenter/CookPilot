import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Plus, Trash2, ShoppingCart, Loader2, Calendar, ChevronLeft, ChevronRight, X, Search } from "lucide-react";

const MEAL_TYPES = [
    { id: "fruehstueck", label: "Frühstück" },
    { id: "mittag", label: "Mittag" },
    { id: "abend", label: "Abend" },
    { id: "snack", label: "Snack" },
];

const WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

function startOfWeek(d) {
    const date = new Date(d);
    const day = (date.getDay() + 6) % 7; // Mon=0
    date.setDate(date.getDate() - day);
    date.setHours(0, 0, 0, 0);
    return date;
}

function isoDate(d) {
    return d.toISOString().slice(0, 10);
}

export default function MealPlan() {
    const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(false);
    const [picker, setPicker] = useState(null); // {date, meal_type}
    const [recipes, setRecipes] = useState([]);
    const [recipeQuery, setRecipeQuery] = useState("");
    const [generating, setGenerating] = useState(false);

    const days = useMemo(() => {
        return Array.from({ length: 7 }, (_, i) => {
            const d = new Date(weekStart);
            d.setDate(d.getDate() + i);
            return d;
        });
    }, [weekStart]);

    const start = isoDate(days[0]);
    const end = isoDate(days[6]);

    const load = async () => {
        setLoading(true);
        try {
            const { data } = await api.get("/meal-plan", { params: { start_date: start, end_date: end } });
            setEntries(data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); /* eslint-disable-next-line */ }, [start, end]);
    useEffect(() => { api.get("/recipes").then((r) => setRecipes(r.data)).catch(() => {}); }, []);

    const entriesFor = (date, meal_type) =>
        entries.filter((e) => e.date === isoDate(date) && e.meal_type === meal_type);

    const addEntry = async (recipe_id, custom_title) => {
        if (!picker) return;
        try {
            await api.post("/meal-plan", {
                date: isoDate(picker.date),
                meal_type: picker.meal_type,
                recipe_id: recipe_id || null,
                custom_title: custom_title || null,
                servings: 2,
            });
            toast.success("Hinzugefügt");
            setPicker(null);
            setRecipeQuery("");
            load();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Fehler");
        }
    };

    const removeEntry = async (id) => {
        await api.delete(`/meal-plan/${id}`);
        setEntries((arr) => arr.filter((e) => e.id !== id));
    };

    const generateShoppingList = async () => {
        setGenerating(true);
        try {
            const { data } = await api.post("/meal-plan/generate-shopping-list", {
                start_date: start, end_date: end, deduct_pantry: true,
            });
            toast.success(`${data.added} neue Artikel · ${data.merged} zusammengeführt · ${data.skipped_pantry} bereits im Vorrat`);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Fehler");
        } finally {
            setGenerating(false);
        }
    };

    const filteredRecipes = recipeQuery
        ? recipes.filter((r) => r.title.toLowerCase().includes(recipeQuery.toLowerCase()))
        : recipes;

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-7xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
                <div>
                    <div className="cp-kicker mb-2">Wochenplan</div>
                    <h1 className="font-display text-4xl sm:text-5xl font-bold">Was kochst du diese Woche?</h1>
                </div>
                <button onClick={generateShoppingList} disabled={generating || entries.length === 0} className="cp-btn-primary" data-testid="generate-shopping-list-btn">
                    {generating ? <Loader2 className="h-5 w-5 animate-spin" /> : <ShoppingCart className="h-5 w-5" />}
                    Einkaufsliste erzeugen
                </button>
            </div>

            <div className="flex items-center justify-between mb-6">
                <button onClick={() => { const d = new Date(weekStart); d.setDate(d.getDate() - 7); setWeekStart(d); }} className="cp-btn-secondary" data-testid="plan-prev-week">
                    <ChevronLeft className="h-4 w-4" /> Vorwoche
                </button>
                <div className="font-display text-lg font-bold flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-[color:var(--primary)]" />
                    {days[0].toLocaleDateString("de-DE", { day: "2-digit", month: "short" })} – {days[6].toLocaleDateString("de-DE", { day: "2-digit", month: "short", year: "numeric" })}
                </div>
                <button onClick={() => { const d = new Date(weekStart); d.setDate(d.getDate() + 7); setWeekStart(d); }} className="cp-btn-secondary" data-testid="plan-next-week">
                    Nächste <ChevronRight className="h-4 w-4" />
                </button>
            </div>

            {loading ? (
                <div className="cp-card text-center py-10"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>
            ) : (
                <div className="overflow-x-auto pb-2">
                    <div className="grid grid-cols-7 gap-3 min-w-[1000px]">
                        {days.map((d, i) => (
                            <div key={i} className="cp-card p-4">
                                <div className="cp-kicker text-[10px] mb-1">{WEEKDAYS[i]}</div>
                                <div className="font-display text-xl font-bold mb-3">{d.getDate()}.{(d.getMonth() + 1).toString().padStart(2, "0")}</div>
                                <div className="space-y-3">
                                    {MEAL_TYPES.map((m) => {
                                        const cur = entriesFor(d, m.id);
                                        return (
                                            <div key={m.id} data-testid={`plan-cell-${isoDate(d)}-${m.id}`}>
                                                <div className="text-xs font-bold text-[color:var(--muted)] uppercase mb-1">{m.label}</div>
                                                {cur.map((e) => (
                                                    <div key={e.id} className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2 text-sm flex items-center justify-between gap-2 mb-1" data-testid={`plan-entry-${e.id}`}>
                                                        {e.recipe ? (
                                                            <Link to={`/recipes/${e.recipe.id}`} className="font-semibold hover:text-[color:var(--primary)] truncate">{e.recipe.title}</Link>
                                                        ) : (
                                                            <span className="font-semibold truncate">{e.custom_title || "—"}</span>
                                                        )}
                                                        <button onClick={() => removeEntry(e.id)} className="text-[color:var(--muted)] hover:text-[color:var(--danger)]" data-testid={`plan-remove-${e.id}`}>
                                                            <Trash2 className="h-3 w-3" />
                                                        </button>
                                                    </div>
                                                ))}
                                                <button
                                                    onClick={() => setPicker({ date: d, meal_type: m.id })}
                                                    className="w-full text-xs py-2 rounded-xl border border-dashed border-[color:var(--border)] hover:border-[color:var(--primary)] hover:text-[color:var(--primary)] text-[color:var(--muted)]"
                                                    data-testid={`plan-add-${isoDate(d)}-${m.id}`}
                                                >
                                                    <Plus className="h-3 w-3 inline" /> Hinzufügen
                                                </button>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {picker && (
                <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4" onClick={() => setPicker(null)}>
                    <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-start justify-between mb-3">
                            <div>
                                <div className="cp-kicker mb-1">{picker.date.toLocaleDateString("de-DE", { weekday: "long", day: "2-digit", month: "long" })}</div>
                                <h3 className="font-display text-2xl font-bold">{MEAL_TYPES.find((m) => m.id === picker.meal_type)?.label}</h3>
                            </div>
                            <button onClick={() => setPicker(null)} className="cp-btn-ghost"><X className="h-5 w-5" /></button>
                        </div>
                        <div className="relative mb-3">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-[color:var(--muted)]" />
                            <input
                                className="cp-input pl-11"
                                placeholder="Rezept suchen oder eigenen Titel eingeben…"
                                value={recipeQuery}
                                onChange={(e) => setRecipeQuery(e.target.value)}
                                autoFocus
                                data-testid="plan-recipe-search"
                            />
                        </div>
                        <div className="overflow-y-auto -mx-2 px-2 flex-1">
                            <div className="space-y-2">
                                {filteredRecipes.slice(0, 50).map((r) => (
                                    <button
                                        key={r.id}
                                        onClick={() => addEntry(r.id, null)}
                                        className="w-full flex items-center gap-3 p-2 rounded-2xl hover:bg-[color:var(--surface-2)] text-left"
                                        data-testid={`plan-pick-recipe-${r.id}`}
                                    >
                                        {r.image_url && <img src={r.image_url} alt="" className="h-12 w-12 rounded-xl object-cover" />}
                                        <div className="flex-1 min-w-0">
                                            <div className="font-semibold truncate">{r.title}</div>
                                            <div className="text-xs text-[color:var(--muted)]">{r.category} · {r.cook_time_min || "?"} Min</div>
                                        </div>
                                    </button>
                                ))}
                                {filteredRecipes.length === 0 && recipeQuery && (
                                    <button onClick={() => addEntry(null, recipeQuery)} className="w-full p-3 rounded-2xl border-2 border-dashed border-[color:var(--border)] hover:border-[color:var(--primary)] text-left" data-testid="plan-pick-custom">
                                        <Plus className="h-4 w-4 inline mr-2" /> „{recipeQuery}" als freien Eintrag hinzufügen
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
