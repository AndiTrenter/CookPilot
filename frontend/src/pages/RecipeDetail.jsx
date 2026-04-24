import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Clock, Heart, Edit, ChefHat, ShoppingCart, Trash2 } from "lucide-react";

export default function RecipeDetail() {
    const { id } = useParams();
    const nav = useNavigate();
    const [r, setR] = useState(null);

    const load = () => api.get(`/recipes/${id}`).then((res) => setR(res.data));
    useEffect(() => { load(); }, [id]); // eslint-disable-line

    const addToShopping = async () => {
        try {
            const { data } = await api.post("/shopping/from-recipe", { recipe_id: id });
            toast.success(`${data.added} Zutaten zur Einkaufsliste`);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Fehler");
        }
    };

    const remove = async () => {
        if (!window.confirm("Rezept wirklich löschen?")) return;
        await api.delete(`/recipes/${id}`);
        toast.success("Gelöscht");
        nav("/recipes");
    };

    const toggleFav = async () => {
        const { data } = await api.post(`/recipes/${id}/favorite`);
        setR(data);
    };

    if (!r) return <div className="p-12 cp-kicker">Laden…</div>;

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-4xl mx-auto">
            <div className="mb-8">
                <div className="cp-kicker mb-2">{r.category || "Ohne Kategorie"}</div>
                <div className="flex items-start justify-between gap-4">
                    <h1 className="font-display text-4xl sm:text-5xl font-bold">{r.title}</h1>
                    <button onClick={toggleFav} data-testid="detail-fav-btn">
                        <Heart className={`h-8 w-8 ${r.favorite ? "fill-[color:var(--primary)] text-[color:var(--primary)]" : "text-[color:var(--muted)]"}`} />
                    </button>
                </div>
                {r.description && <p className="text-lg text-[color:var(--muted)] mt-3">{r.description}</p>}
                {r.image_url && (
                    <div className="mt-6 rounded-3xl overflow-hidden aspect-video bg-[color:var(--surface-2)]">
                        <img src={r.image_url} alt={r.title} className="w-full h-full object-cover" />
                    </div>
                )}
                <div className="flex flex-wrap gap-2 mt-4">
                    {r.difficulty && <span className="cp-chip">{r.difficulty}</span>}
                    {r.cook_time_min && <span className="cp-chip"><Clock className="h-3 w-3 mr-1" /> {r.cook_time_min} Min</span>}
                    <span className="cp-chip">{r.servings} Portionen</span>
                    {r.source && r.source.startsWith("lidl:") && <span className="cp-chip cp-chip-ok">aus rezepte.lidl.ch</span>}
                </div>
            </div>

            <div className="flex flex-wrap gap-2 mb-8">
                <Link to={`/recipes/${id}/cook`} className="cp-btn-primary" data-testid="start-cooking-btn">
                    <ChefHat className="h-5 w-5" /> Kochen starten
                </Link>
                <button onClick={addToShopping} className="cp-btn-secondary" data-testid="add-to-shopping-btn">
                    <ShoppingCart className="h-5 w-5" /> Zur Einkaufsliste
                </button>
                <Link to={`/recipes/${id}/edit`} className="cp-btn-secondary" data-testid="edit-recipe-btn">
                    <Edit className="h-5 w-5" /> Bearbeiten
                </Link>
                <button onClick={remove} className="cp-btn-ghost text-[color:var(--danger)]" data-testid="delete-recipe-detail-btn">
                    <Trash2 className="h-5 w-5" /> Löschen
                </button>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
                <section className="cp-card">
                    <h2 className="font-display text-2xl font-bold mb-5">Zutaten</h2>
                    <ul className="space-y-2">
                        {r.ingredients.length === 0 && <li className="text-[color:var(--muted)]">Keine Zutaten.</li>}
                        {r.ingredients.map((ing, i) => (
                            <li key={i} className="flex justify-between border-b border-[color:var(--border)] py-2 last:border-0">
                                <span>{ing.name}</span>
                                <span className="text-[color:var(--muted)]">{ing.amount} {ing.unit}</span>
                            </li>
                        ))}
                    </ul>
                </section>

                <section className="cp-card">
                    <h2 className="font-display text-2xl font-bold mb-5">Zubereitung</h2>
                    <ol className="space-y-4">
                        {r.steps.length === 0 && <li className="text-[color:var(--muted)]">Keine Schritte.</li>}
                        {r.steps.map((s, i) => (
                            <li key={i} className="flex gap-3">
                                <span className="h-7 w-7 rounded-full bg-[color:var(--primary)] text-white font-bold text-xs flex items-center justify-center shrink-0 mt-1">{i + 1}</span>
                                <span className="leading-relaxed">{s}</span>
                            </li>
                        ))}
                    </ol>
                </section>
            </div>
        </div>
    );
}
