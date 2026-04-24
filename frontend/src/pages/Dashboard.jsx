import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import {
    ShoppingCart,
    Archive,
    BookOpen,
    MessageSquare,
    AlertTriangle,
    Heart,
    ChevronRight,
    Tablet,
    Camera,
    Receipt,
} from "lucide-react";

export default function Dashboard() {
    const { user } = useAuth();
    const [data, setData] = useState({ recipes: [], favorites: [], shopping: [], lowStock: [] });

    useEffect(() => {
        (async () => {
            try {
                const [recipes, favs, shop, low] = await Promise.all([
                    api.get("/recipes").then((r) => r.data),
                    api.get("/recipes", { params: { favorite: true } }).then((r) => r.data),
                    api.get("/shopping").then((r) => r.data),
                    api.get("/pantry/low-stock").then((r) => r.data),
                ]);
                setData({ recipes, favorites: favs, shopping: shop, lowStock: low });
            } catch (e) {
                /* ignore on first boot */
            }
        })();
    }, []);

    const openShop = data.shopping.filter((i) => !i.checked).length;
    const hour = new Date().getHours();
    const greeting = hour < 11 ? "Guten Morgen" : hour < 18 ? "Guten Tag" : "Guten Abend";

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-7xl mx-auto">
            <div className="mb-10">
                <div className="cp-kicker mb-3">Heute · {new Date().toLocaleDateString("de-DE", { weekday: "long", day: "2-digit", month: "long" })}</div>
                <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
                    {greeting}, <span className="text-[color:var(--primary)]">{user?.name?.split(" ")[0] || "Koch"}</span>.
                </h1>
                <p className="text-[color:var(--muted)] mt-3 text-lg">Was steht heute auf dem Tisch?</p>
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-10">
                <StatTile testid="stat-recipes" to="/recipes" Icon={BookOpen} value={data.recipes.length} label="Rezepte" />
                <StatTile testid="stat-shopping" to="/shopping" Icon={ShoppingCart} value={openShop} label="Offene Artikel" accent={openShop > 0} />
                <StatTile testid="stat-lowstock" to="/pantry" Icon={AlertTriangle} value={data.lowStock.length} label="Niedriger Bestand" warn={data.lowStock.length > 0} />
                <StatTile testid="stat-favorites" to="/recipes?favorite=1" Icon={Heart} value={data.favorites.length} label="Favoriten" />
            </div>

            <div className="grid md:grid-cols-2 gap-6 lg:gap-8">
                <section className="cp-card">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="font-display text-2xl font-bold">Einkaufsliste</h2>
                        <Link to="/shopping" className="cp-btn-ghost text-sm" data-testid="open-shopping-link">Öffnen <ChevronRight className="h-4 w-4" /></Link>
                    </div>
                    {data.shopping.length === 0 ? (
                        <Empty label="Noch nichts auf der Liste." />
                    ) : (
                        <ul className="space-y-3">
                            {data.shopping.slice(0, 5).map((i) => (
                                <li key={i.id} className="flex items-center justify-between">
                                    <div>
                                        <div className={`font-semibold ${i.checked ? "line-through text-[color:var(--muted)]" : ""}`}>{i.name}</div>
                                        <div className="text-xs text-[color:var(--muted)]">{i.amount} {i.unit}</div>
                                    </div>
                                    {i.checked && <span className="cp-chip cp-chip-ok">erledigt</span>}
                                </li>
                            ))}
                        </ul>
                    )}
                </section>

                <section className="cp-card">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="font-display text-2xl font-bold">Bestandswarnungen</h2>
                        <Link to="/pantry" className="cp-btn-ghost text-sm" data-testid="open-pantry-link">Vorrat <ChevronRight className="h-4 w-4" /></Link>
                    </div>
                    {data.lowStock.length === 0 ? (
                        <Empty label="Alles auf Lager." />
                    ) : (
                        <ul className="space-y-3">
                            {data.lowStock.slice(0, 5).map((p) => (
                                <li key={p.id} className="flex items-center justify-between">
                                    <div className="font-semibold">{p.name}</div>
                                    <span className="cp-chip cp-chip-warn">
                                        {p.amount}/{p.min_amount} {p.unit}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    )}
                </section>

                <section className="cp-card">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="font-display text-2xl font-bold">Favoriten</h2>
                        <Link to="/recipes?favorite=1" className="cp-btn-ghost text-sm" data-testid="open-favorites-link">Alle <ChevronRight className="h-4 w-4" /></Link>
                    </div>
                    {data.favorites.length === 0 ? (
                        <Empty label="Noch keine Favoriten." />
                    ) : (
                        <ul className="grid grid-cols-2 gap-3">
                            {data.favorites.slice(0, 4).map((r) => (
                                <Link key={r.id} to={`/recipes/${r.id}`} className="cp-tile block">
                                    <div className="font-semibold">{r.title}</div>
                                    <div className="text-xs text-[color:var(--muted)]">{r.category || "—"} · {r.cook_time_min || "?"} Min</div>
                                </Link>
                            ))}
                        </ul>
                    )}
                </section>

                <section className="cp-card">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="font-display text-2xl font-bold">Schnellzugriff</h2>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <Link to="/chat" className="cp-tile flex flex-col gap-2" data-testid="quick-chat">
                            <MessageSquare className="h-6 w-6 text-[color:var(--primary)]" strokeWidth={2.5} />
                            <div className="font-semibold">Koch-Chat</div>
                            <div className="text-xs text-[color:var(--muted)]">Fragen an die KI</div>
                        </Link>
                        <Link to="/recipes/new" className="cp-tile flex flex-col gap-2" data-testid="quick-new-recipe">
                            <BookOpen className="h-6 w-6 text-[color:var(--primary)]" strokeWidth={2.5} />
                            <div className="font-semibold">Rezept anlegen</div>
                            <div className="text-xs text-[color:var(--muted)]">Neu erstellen</div>
                        </Link>
                        <Link to="/tablet" className="cp-tile flex flex-col gap-2" data-testid="quick-tablet">
                            <Tablet className="h-6 w-6 text-[color:var(--primary)]" strokeWidth={2.5} />
                            <div className="font-semibold">Tablet-Modus</div>
                            <div className="text-xs text-[color:var(--muted)]">Wand-Ansicht</div>
                        </Link>
                        <Link to="/scan" className="cp-tile flex flex-col gap-2" data-testid="quick-scan">
                            <Camera className="h-6 w-6 text-[color:var(--primary)]" strokeWidth={2.5} />
                            <div className="font-semibold">Einkauf einräumen</div>
                            <div className="text-xs text-[color:var(--muted)]">Fotos scannen</div>
                        </Link>
                        <Link to="/receipt-scan" className="cp-tile flex flex-col gap-2" data-testid="quick-receipt">
                            <Receipt className="h-6 w-6 text-[color:var(--primary)]" strokeWidth={2.5} />
                            <div className="font-semibold">Kassenzettel</div>
                            <div className="text-xs text-[color:var(--muted)]">Auswerten</div>
                        </Link>
                        <Link to="/pantry" className="cp-tile flex flex-col gap-2" data-testid="quick-pantry">
                            <Archive className="h-6 w-6 text-[color:var(--primary)]" strokeWidth={2.5} />
                            <div className="font-semibold">Vorrat</div>
                            <div className="text-xs text-[color:var(--muted)]">Bestand prüfen</div>
                        </Link>
                    </div>
                </section>
            </div>
        </div>
    );
}

function StatTile({ Icon, value, label, to, accent, warn, testid }) {
    return (
        <Link to={to} className="cp-tile block" data-testid={testid}>
            <Icon
                className={`h-6 w-6 mb-3 ${accent ? "text-[color:var(--primary)]" : warn ? "text-[color:var(--warning)]" : "text-[color:var(--muted)]"}`}
                strokeWidth={2.5}
            />
            <div className="font-display text-3xl font-bold">{value}</div>
            <div className="text-xs mt-1 text-[color:var(--muted)] uppercase tracking-wider font-bold">{label}</div>
        </Link>
    );
}

function Empty({ label }) {
    return <div className="text-[color:var(--muted)] text-sm py-6 text-center">{label}</div>;
}
