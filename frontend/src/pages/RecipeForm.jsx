import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Save } from "lucide-react";
import ProductInput from "../components/ProductInput";
import UnitSelect from "../components/UnitSelect";

const emptyRecipe = {
    title: "",
    description: "",
    category: "",
    tags: [],
    servings: 2,
    cook_time_min: 30,
    difficulty: "mittel",
    ingredients: [{ name: "", amount: 0, unit: "" }],
    steps: [""],
    favorite: false,
    image_url: "",
};

export default function RecipeForm() {
    const { id } = useParams();
    const nav = useNavigate();
    const isEdit = Boolean(id);
    const [r, setR] = useState(emptyRecipe);
    const [loading, setLoading] = useState(isEdit);

    useEffect(() => {
        if (!isEdit) return;
        api.get(`/recipes/${id}`)
            .then((res) => setR(res.data))
            .finally(() => setLoading(false));
    }, [id, isEdit]);

    const save = async () => {
        if (!r.title.trim()) {
            toast.error("Titel fehlt");
            return;
        }
        try {
            const payload = {
                ...r,
                ingredients: (r.ingredients || []).filter((i) => i.name.trim()),
                steps: (r.steps || []).filter((s) => s.trim()),
            };
            if (isEdit) {
                await api.patch(`/recipes/${id}`, payload);
                toast.success("Gespeichert");
            } else {
                const { data } = await api.post("/recipes", payload);
                toast.success("Rezept angelegt");
                nav(`/recipes/${data.id}`);
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Fehler");
        }
    };

    if (loading) return <div className="p-12 cp-kicker">Laden…</div>;

    const updateIng = (idx, field, val) => {
        const arr = [...r.ingredients];
        arr[idx] = { ...arr[idx], [field]: val };
        setR({ ...r, ingredients: arr });
    };

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-8">
                <h1 className="font-display text-4xl font-bold">{isEdit ? "Rezept bearbeiten" : "Neues Rezept"}</h1>
                <button onClick={save} className="cp-btn-primary" data-testid="save-recipe-btn">
                    <Save className="h-5 w-5" /> Speichern
                </button>
            </div>

            <div className="space-y-6">
                <div className="cp-card">
                    <div className="space-y-5">
                        <div>
                            <label className="cp-label">Titel</label>
                            <input className="cp-input" value={r.title} onChange={(e) => setR({ ...r, title: e.target.value })} data-testid="recipe-title-input" />
                        </div>
                        <div>
                            <label className="cp-label">Beschreibung</label>
                            <textarea rows={3} className="cp-input" value={r.description} onChange={(e) => setR({ ...r, description: e.target.value })} data-testid="recipe-description-input" />
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            <div>
                                <label className="cp-label">Kategorie</label>
                                <input className="cp-input" value={r.category} onChange={(e) => setR({ ...r, category: e.target.value })} placeholder="z.B. Mittag" data-testid="recipe-category-input" />
                            </div>
                            <div>
                                <label className="cp-label">Portionen</label>
                                <input type="number" min={1} className="cp-input" value={r.servings} onChange={(e) => setR({ ...r, servings: +e.target.value })} data-testid="recipe-servings-input" />
                            </div>
                            <div>
                                <label className="cp-label">Zeit (Min)</label>
                                <input type="number" min={0} className="cp-input" value={r.cook_time_min || 0} onChange={(e) => setR({ ...r, cook_time_min: +e.target.value })} data-testid="recipe-time-input" />
                            </div>
                            <div>
                                <label className="cp-label">Schwierigkeit</label>
                                <select className="cp-input" value={r.difficulty || ""} onChange={(e) => setR({ ...r, difficulty: e.target.value })} data-testid="recipe-difficulty-select">
                                    <option value="">—</option>
                                    <option value="leicht">leicht</option>
                                    <option value="mittel">mittel</option>
                                    <option value="schwer">schwer</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="cp-card">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="font-display text-2xl font-bold">Zutaten</h2>
                        <button
                            onClick={() => setR({ ...r, ingredients: [...r.ingredients, { name: "", amount: 0, unit: "" }] })}
                            className="cp-btn-secondary"
                            data-testid="add-ingredient-btn"
                        >
                            <Plus className="h-4 w-4" /> Hinzufügen
                        </button>
                    </div>
                    <div className="space-y-3">
                        {r.ingredients.map((ing, i) => (
                            <div key={i} className="grid grid-cols-12 gap-2">
                                <input className="cp-input col-span-2" type="number" min={0} step="0.1" value={ing.amount} onChange={(e) => updateIng(i, "amount", +e.target.value)} data-testid={`ing-amount-${i}`} />
                                <div className="col-span-2">
                                    <UnitSelect
                                        value={ing.unit}
                                        onChange={(v) => updateIng(i, "unit", v)}
                                        testId={`ing-unit-${i}`}
                                    />
                                </div>
                                <div className="col-span-7">
                                    <ProductInput
                                        value={ing.name}
                                        onChange={(v) => updateIng(i, "name", v)}
                                        onUnitSelect={(u) => updateIng(i, "unit", u)}
                                        placeholder="Zutat"
                                        testId={`ing-name-${i}`}
                                    />
                                </div>
                                <button onClick={() => setR({ ...r, ingredients: r.ingredients.filter((_, idx) => idx !== i) })} className="cp-btn-ghost text-[color:var(--danger)] col-span-1" data-testid={`ing-del-${i}`}>
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="cp-card">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="font-display text-2xl font-bold">Zubereitung</h2>
                        <button
                            onClick={() => setR({ ...r, steps: [...r.steps, ""] })}
                            className="cp-btn-secondary"
                            data-testid="add-step-btn"
                        >
                            <Plus className="h-4 w-4" /> Schritt
                        </button>
                    </div>
                    <ol className="space-y-3">
                        {r.steps.map((s, i) => (
                            <li key={i} className="flex gap-3 items-start">
                                <span className="mt-3 h-8 w-8 rounded-full bg-[color:var(--primary)] text-white font-bold text-sm flex items-center justify-center shrink-0">{i + 1}</span>
                                <textarea
                                    rows={2}
                                    className="cp-input flex-1"
                                    value={s}
                                    onChange={(e) => {
                                        const arr = [...r.steps];
                                        arr[i] = e.target.value;
                                        setR({ ...r, steps: arr });
                                    }}
                                    data-testid={`step-input-${i}`}
                                />
                                <button onClick={() => setR({ ...r, steps: r.steps.filter((_, idx) => idx !== i) })} className="cp-btn-ghost text-[color:var(--danger)] mt-3" data-testid={`step-del-${i}`}>
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </li>
                        ))}
                    </ol>
                </div>
            </div>
        </div>
    );
}
