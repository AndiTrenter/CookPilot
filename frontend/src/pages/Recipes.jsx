import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Heart, Plus, Search, Clock, ChefHat, Trash2 } from "lucide-react";

export default function Recipes() {
    const [params, setParams] = useSearchParams();
    const [items, setItems] = useState([]);
    const [search, setSearch] = useState("");
    const [onlyFav, setOnlyFav] = useState(params.get("favorite") === "1");

    const load = async () => {
        const q = {};
        if (search) q.search = search;
        if (onlyFav) q.favorite = true;
        const { data } = await api.get("/recipes", { params: q });
        setItems(data);
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [onlyFav]);

    const remove = async (id) => {
        if (!window.confirm("Rezept wirklich löschen?")) return;
        await api.delete(`/recipes/${id}`);
        toast.success("Gelöscht");
        load();
    };

    const toggleFav = async (id) => {
        const { data } = await api.post(`/recipes/${id}/favorite`);
        setItems((list) => list.map((r) => (r.id === id ? data : r)));
    };

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-7xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
                <div>
                    <div className="cp-kicker mb-2">Deine Rezeptsammlung</div>
                    <h1 className="font-display text-4xl sm:text-5xl font-bold">Rezepte</h1>
                </div>
                <Link to="/recipes/new" className="cp-btn-primary" data-testid="new-recipe-btn">
                    <Plus className="h-5 w-5" /> Neues Rezept
                </Link>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 mb-8">
                <div className="relative flex-1">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[color:var(--muted)]" />
                    <input
                        className="cp-input pl-12"
                        placeholder="Suchen nach Titel, Kategorie, Tag…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && load()}
                        data-testid="recipe-search-input"
                    />
                </div>
                <button
                    onClick={() => {
                        const v = !onlyFav;
                        setOnlyFav(v);
                        setParams(v ? { favorite: "1" } : {});
                    }}
                    className={`cp-btn-secondary ${onlyFav ? "border-[color:var(--primary)] text-[color:var(--primary)]" : ""}`}
                    data-testid="recipe-favorite-filter"
                >
                    <Heart className={`h-4 w-4 ${onlyFav ? "fill-[color:var(--primary)]" : ""}`} />
                    Favoriten
                </button>
                <button onClick={load} className="cp-btn-secondary" data-testid="recipe-search-btn">Suchen</button>
            </div>

            {items.length === 0 ? (
                <div className="cp-card text-center py-16">
                    <ChefHat className="h-12 w-12 mx-auto mb-4 text-[color:var(--muted)]" strokeWidth={2} />
                    <p className="text-[color:var(--muted)] mb-6">Noch keine Rezepte vorhanden.</p>
                    <Link to="/recipes/new" className="cp-btn-primary">Erstes Rezept anlegen</Link>
                </div>
            ) : (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {items.map((r) => (
                        <div key={r.id} className="cp-tile flex flex-col gap-3" data-testid={`recipe-card-${r.id}`}>
                            <div className="flex items-start justify-between gap-2">
                                <Link to={`/recipes/${r.id}`} className="font-display text-xl font-bold hover:text-[color:var(--primary)]">
                                    {r.title}
                                </Link>
                                <button onClick={() => toggleFav(r.id)} data-testid={`recipe-fav-${r.id}`}>
                                    <Heart className={`h-5 w-5 ${r.favorite ? "fill-[color:var(--primary)] text-[color:var(--primary)]" : "text-[color:var(--muted)]"}`} />
                                </button>
                            </div>
                            <p className="text-sm text-[color:var(--muted)] line-clamp-2">{r.description || "Keine Beschreibung"}</p>
                            <div className="flex flex-wrap gap-2 mt-1">
                                {r.category && <span className="cp-chip">{r.category}</span>}
                                {r.difficulty && <span className="cp-chip">{r.difficulty}</span>}
                                {r.cook_time_min && (
                                    <span className="cp-chip">
                                        <Clock className="h-3 w-3 mr-1" /> {r.cook_time_min} Min
                                    </span>
                                )}
                            </div>
                            <div className="flex gap-2 mt-auto pt-4 border-t border-[color:var(--border)]">
                                <Link to={`/recipes/${r.id}/cook`} className="cp-btn-secondary flex-1" data-testid={`cook-btn-${r.id}`}>Kochen</Link>
                                <Link to={`/recipes/${r.id}`} className="cp-btn-ghost">Details</Link>
                                <button onClick={() => remove(r.id)} className="cp-btn-ghost text-[color:var(--danger)]" data-testid={`delete-recipe-${r.id}`}>
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
