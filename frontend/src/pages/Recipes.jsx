import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Heart, Plus, Search, Clock, ChefHat, Trash2, Link2, Download, RefreshCw, Loader2, Globe } from "lucide-react";

export default function Recipes() {
    const nav = useNavigate();
    const [params, setParams] = useSearchParams();
    const [items, setItems] = useState([]);
    const [search, setSearch] = useState("");
    const [onlyFav, setOnlyFav] = useState(params.get("favorite") === "1");
    const [external, setExternal] = useState({ results: [], count: 0 });
    const [extStatus, setExtStatus] = useState(null);
    const [extLoading, setExtLoading] = useState(false);
    const [importing, setImporting] = useState({});
    const [refreshing, setRefreshing] = useState(false);
    const [showImport, setShowImport] = useState(false);
    const [importUrl, setImportUrl] = useState("");
    const [importBusy, setImportBusy] = useState(false);

    const loadLocal = async () => {
        const q = {};
        if (search) q.search = search;
        if (onlyFav) q.favorite = true;
        const { data } = await api.get("/recipes", { params: q });
        setItems(data);
    };

    const loadExternal = async (query) => {
        setExtLoading(true);
        try {
            const { data } = await api.get("/recipes/external/search", { params: { q: query || "" } });
            setExternal(data);
        } catch {
            setExternal({ results: [], count: 0 });
        } finally {
            setExtLoading(false);
        }
    };

    const loadStatus = async () => {
        try {
            const { data } = await api.get("/recipes/external/status");
            setExtStatus(data);
        } catch { /* ignore */ }
    };

    useEffect(() => {
        loadLocal();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [onlyFav]);

    useEffect(() => { loadStatus(); loadExternal(""); }, []);

    const runSearch = async () => {
        await Promise.all([loadLocal(), loadExternal(search)]);
    };

    const remove = async (id) => {
        if (!window.confirm("Rezept wirklich löschen?")) return;
        await api.delete(`/recipes/${id}`);
        toast.success("Gelöscht");
        loadLocal();
    };

    const toggleFav = async (id) => {
        const { data } = await api.post(`/recipes/${id}/favorite`);
        setItems((list) => list.map((r) => (r.id === id ? data : r)));
    };

    const importFromUrl = async (url) => {
        setImportBusy(true);
        try {
            const { data } = await api.post("/recipes/import-url", { url });
            toast.success(`"${data.title}" importiert`);
            setShowImport(false);
            setImportUrl("");
            nav(`/recipes/${data.id}`);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Import fehlgeschlagen");
        } finally {
            setImportBusy(false);
        }
    };

    const importExternal = async (source_url, slug) => {
        setImporting((m) => ({ ...m, [slug]: true }));
        try {
            const { data } = await api.post("/recipes/import-url", { url: source_url });
            toast.success(`"${data.title}" in dein Rezeptbuch übernommen`);
            loadLocal();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Import fehlgeschlagen");
        } finally {
            setImporting((m) => ({ ...m, [slug]: false }));
        }
    };

    const refreshIndex = async () => {
        setRefreshing(true);
        try {
            const { data } = await api.post("/recipes/external/refresh");
            toast.success(`${data.indexed} Rezepte aktualisiert`);
            await loadStatus();
            await loadExternal(search);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Aktualisierung fehlgeschlagen");
        } finally {
            setRefreshing(false);
        }
    };

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-7xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
                <div>
                    <div className="cp-kicker mb-2">Deine Rezeptsammlung</div>
                    <h1 className="font-display text-4xl sm:text-5xl font-bold">Rezepte</h1>
                </div>
                <div className="flex flex-wrap gap-2">
                    <button onClick={() => setShowImport(true)} className="cp-btn-secondary" data-testid="import-url-btn">
                        <Link2 className="h-4 w-4" /> Aus Link importieren
                    </button>
                    <Link to="/recipes/new" className="cp-btn-primary" data-testid="new-recipe-btn">
                        <Plus className="h-5 w-5" /> Neues Rezept
                    </Link>
                </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 mb-8">
                <div className="relative flex-1">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[color:var(--muted)]" />
                    <input
                        className="cp-input pl-12"
                        placeholder="Deine Rezepte und rezepte.lidl.ch durchsuchen…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && runSearch()}
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
                <button onClick={runSearch} className="cp-btn-primary" data-testid="recipe-search-btn">
                    <Search className="h-4 w-4" /> Suchen
                </button>
            </div>

            {/* Local recipes */}
            <section className="mb-12">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="font-display text-2xl font-bold">Deine Rezepte <span className="text-[color:var(--muted)] text-base font-normal">({items.length})</span></h2>
                </div>
                {items.length === 0 ? (
                    <div className="cp-card text-center py-12">
                        <ChefHat className="h-10 w-10 mx-auto mb-3 text-[color:var(--muted)]" strokeWidth={2} />
                        <p className="text-[color:var(--muted)] mb-4">Noch keine eigenen Rezepte. Lege eins an, importiere per Link oder übernimm eines aus den Treffern unten.</p>
                        <Link to="/recipes/new" className="cp-btn-primary">Erstes Rezept anlegen</Link>
                    </div>
                ) : (
                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        {items.map((r) => (
                            <div key={r.id} className="cp-tile flex flex-col gap-3" data-testid={`recipe-card-${r.id}`}>
                                {r.image_url && (
                                    <Link to={`/recipes/${r.id}`} className="block -mx-6 -mt-6 mb-1 aspect-video overflow-hidden rounded-t-3xl bg-[color:var(--surface-2)]">
                                        <img src={r.image_url} alt="" className="w-full h-full object-cover" loading="lazy" />
                                    </Link>
                                )}
                                <div className="flex items-start justify-between gap-2">
                                    <Link to={`/recipes/${r.id}`} className="font-display text-xl font-bold hover:text-[color:var(--primary)]">
                                        {r.title}
                                    </Link>
                                    <button onClick={() => toggleFav(r.id)} data-testid={`recipe-fav-${r.id}`}>
                                        <Heart className={`h-5 w-5 ${r.favorite ? "fill-[color:var(--primary)] text-[color:var(--primary)]" : "text-[color:var(--muted)]"}`} />
                                    </button>
                                </div>
                                <p className="text-sm text-[color:var(--muted)] line-clamp-2">{r.description || ""}</p>
                                <div className="flex flex-wrap gap-2 mt-1">
                                    {r.category && <span className="cp-chip">{r.category}</span>}
                                    {r.difficulty && <span className="cp-chip">{r.difficulty}</span>}
                                    {r.cook_time_min && (
                                        <span className="cp-chip"><Clock className="h-3 w-3 mr-1" /> {r.cook_time_min} Min</span>
                                    )}
                                    {r.source && r.source.startsWith("lidl:") && <span className="cp-chip cp-chip-ok">Lidl</span>}
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
            </section>

            {/* External results */}
            <section>
                <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-4">
                    <div>
                        <h2 className="font-display text-2xl font-bold flex items-center gap-2">
                            <Globe className="h-6 w-6 text-[color:var(--primary)]" /> Aus rezepte.lidl.ch
                        </h2>
                        <p className="text-xs text-[color:var(--muted)] mt-1">
                            {extStatus?.count ? `${extStatus.count} Rezepte im Cache · zuletzt aktualisiert ${extStatus.last_indexed_at ? new Date(extStatus.last_indexed_at).toLocaleString("de-DE") : "nie"}` : "Noch kein Index - bitte aktualisieren"}
                        </p>
                    </div>
                    <button onClick={refreshIndex} disabled={refreshing} className="cp-btn-secondary" data-testid="refresh-external-btn">
                        {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Index aktualisieren
                    </button>
                </div>

                {extLoading ? (
                    <div className="cp-card py-8 text-center text-[color:var(--muted)]"><Loader2 className="h-6 w-6 animate-spin inline mr-2" /> Suche…</div>
                ) : external.count === 0 ? (
                    <div className="cp-card text-center py-10 text-[color:var(--muted)]">Keine Treffer bei rezepte.lidl.ch für „{search || "…"}".</div>
                ) : (
                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        {external.results.map((r) => (
                            <div key={r.slug} className="cp-tile flex flex-col gap-3" data-testid={`external-card-${r.slug}`}>
                                {r.image_url && (
                                    <a href={r.source_url} target="_blank" rel="noreferrer" className="block -mx-6 -mt-6 mb-1 aspect-video overflow-hidden rounded-t-3xl bg-[color:var(--surface-2)]">
                                        <img src={r.image_url} alt="" className="w-full h-full object-cover" loading="lazy" />
                                    </a>
                                )}
                                <h3 className="font-display text-lg font-bold leading-snug">{r.title}</h3>
                                <div className="flex flex-wrap gap-2">
                                    <span className="cp-chip cp-chip-ok">Lidl</span>
                                    {r.difficulty && <span className="cp-chip">{r.difficulty}</span>}
                                    {r.cook_time_min && <span className="cp-chip"><Clock className="h-3 w-3 mr-1" /> {r.cook_time_min} Min</span>}
                                </div>
                                <div className="flex gap-2 mt-auto pt-4 border-t border-[color:var(--border)]">
                                    <button
                                        onClick={() => importExternal(r.source_url, r.slug)}
                                        disabled={importing[r.slug]}
                                        className="cp-btn-primary flex-1"
                                        data-testid={`import-external-${r.slug}`}
                                    >
                                        {importing[r.slug] ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                                        In Rezeptbuch
                                    </button>
                                    <a href={r.source_url} target="_blank" rel="noreferrer" className="cp-btn-ghost" data-testid={`external-open-${r.slug}`}>
                                        <Globe className="h-4 w-4" />
                                    </a>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Import URL modal */}
            {showImport && (
                <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4" onClick={() => !importBusy && setShowImport(false)}>
                    <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
                        <div className="cp-kicker mb-2">Rezept-Import</div>
                        <h3 className="font-display text-2xl font-bold mb-4">Aus URL importieren</h3>
                        <p className="text-sm text-[color:var(--muted)] mb-4">
                            Unterstützt werden aktuell Rezepte von <strong>rezepte.lidl.ch</strong>. Füge einfach die URL eines Rezepts ein.
                        </p>
                        <input
                            className="cp-input mb-4"
                            placeholder="https://rezepte.lidl.ch/rezepte/..."
                            value={importUrl}
                            onChange={(e) => setImportUrl(e.target.value)}
                            autoFocus
                            data-testid="import-url-input"
                        />
                        <div className="flex gap-2 justify-end">
                            <button onClick={() => setShowImport(false)} disabled={importBusy} className="cp-btn-ghost" data-testid="import-url-cancel">Abbrechen</button>
                            <button onClick={() => importFromUrl(importUrl.trim())} disabled={importBusy || !importUrl.trim()} className="cp-btn-primary" data-testid="import-url-confirm">
                                {importBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                                Importieren
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
