import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import {
    ShoppingCart,
    Archive,
    BookOpen,
    MessageSquare,
    Heart,
    AlertTriangle,
    ChefHat,
    X,
} from "lucide-react";

const ICONS = {
    quick_actions: ChefHat,
    shopping_list: ShoppingCart,
    low_stock: AlertTriangle,
    mhd_soon: AlertTriangle,
    favorites: Heart,
    recipe_of_day: BookOpen,
    chat_quick: MessageSquare,
    pantry_summary: Archive,
};

export default function Tablet() {
    const [widgets, setWidgets] = useState([]);
    const [shop, setShop] = useState([]);
    const [low, setLow] = useState([]);
    const [favs, setFavs] = useState([]);
    const [recipes, setRecipes] = useState([]);
    const [pantry, setPantry] = useState([]);

    useEffect(() => {
        (async () => {
            const [w, s, l, f, r, p] = await Promise.all([
                api.get("/widgets/tablet").then((x) => x.data),
                api.get("/shopping").then((x) => x.data),
                api.get("/pantry/low-stock").then((x) => x.data),
                api.get("/recipes", { params: { favorite: true } }).then((x) => x.data),
                api.get("/recipes").then((x) => x.data),
                api.get("/pantry").then((x) => x.data),
            ]);
            setWidgets(w.filter((x) => x.visible !== false));
            setShop(s);
            setLow(l);
            setFavs(f);
            setRecipes(r);
            setPantry(p);
        })();
    }, []);

    const time = new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
    const date = new Date().toLocaleDateString("de-DE", { weekday: "long", day: "2-digit", month: "long" });
    const todayPick = recipes[Math.floor(Math.random() * Math.max(1, recipes.length))];

    return (
        <div className="min-h-screen bg-[color:var(--bg)] p-6 md:p-10">
            <header className="flex items-start justify-between mb-8">
                <div>
                    <div className="cp-kicker mb-1">Küchen-Tablet</div>
                    <h1 className="font-display text-5xl md:text-7xl font-bold tracking-tight">{time}</h1>
                    <div className="text-lg text-[color:var(--muted)] mt-1">{date}</div>
                </div>
                <Link to="/" className="cp-btn-secondary min-h-[64px]" data-testid="tablet-exit-btn">
                    <X className="h-6 w-6" /> Zurück
                </Link>
            </header>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-6 md:gap-8 auto-rows-[180px] md:auto-rows-[200px]">
                {widgets.map((w) => {
                    const Icon = ICONS[w.widget] || ChefHat;
                    if (w.widget === "shopping_list") {
                        const open = shop.filter((i) => !i.checked);
                        return (
                            <TileLink key={w.widget + w.order} to="/shopping" className="col-span-2 row-span-2" testid={`tablet-widget-${w.widget}`}>
                                <div className="flex items-center justify-between mb-4">
                                    <span className="cp-kicker">Einkaufsliste</span>
                                    <Icon className="h-7 w-7 text-[color:var(--primary)]" strokeWidth={2.5} />
                                </div>
                                <div className="font-display text-5xl font-bold mb-4">{open.length}</div>
                                <div className="text-[color:var(--muted)]">offene Artikel</div>
                                <ul className="mt-4 space-y-1 text-base">
                                    {open.slice(0, 4).map((i) => (
                                        <li key={i.id} className="truncate">· {i.name}</li>
                                    ))}
                                </ul>
                            </TileLink>
                        );
                    }
                    if (w.widget === "low_stock") {
                        return (
                            <TileLink key={w.widget + w.order} to="/pantry" testid={`tablet-widget-${w.widget}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="cp-kicker">Niedriger Bestand</span>
                                    <Icon className="h-7 w-7 text-[color:var(--warning)]" strokeWidth={2.5} />
                                </div>
                                <div className="font-display text-5xl font-bold">{low.length}</div>
                            </TileLink>
                        );
                    }
                    if (w.widget === "favorites") {
                        return (
                            <TileLink key={w.widget + w.order} to="/recipes?favorite=1" testid={`tablet-widget-${w.widget}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="cp-kicker">Favoriten</span>
                                    <Icon className="h-7 w-7 text-[color:var(--primary)]" strokeWidth={2.5} />
                                </div>
                                <div className="font-display text-5xl font-bold">{favs.length}</div>
                            </TileLink>
                        );
                    }
                    if (w.widget === "recipe_of_day" && todayPick) {
                        return (
                            <TileLink key={w.widget + w.order} to={`/recipes/${todayPick.id}`} className="col-span-2" testid={`tablet-widget-${w.widget}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="cp-kicker">Rezept des Tages</span>
                                    <Icon className="h-7 w-7 text-[color:var(--primary)]" strokeWidth={2.5} />
                                </div>
                                <div className="font-display text-3xl font-bold">{todayPick.title}</div>
                                <div className="text-[color:var(--muted)] mt-2">{todayPick.category} · {todayPick.cook_time_min || "?"} Min</div>
                            </TileLink>
                        );
                    }
                    if (w.widget === "chat_quick") {
                        return (
                            <TileLink key={w.widget + w.order} to="/chat" testid={`tablet-widget-${w.widget}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="cp-kicker">Koch-Chat</span>
                                    <Icon className="h-7 w-7 text-[color:var(--primary)]" strokeWidth={2.5} />
                                </div>
                                <div className="text-xl font-semibold leading-snug">Frag die KI</div>
                            </TileLink>
                        );
                    }
                    if (w.widget === "pantry_summary") {
                        return (
                            <TileLink key={w.widget + w.order} to="/pantry" testid={`tablet-widget-${w.widget}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="cp-kicker">Vorrat</span>
                                    <Icon className="h-7 w-7 text-[color:var(--primary)]" strokeWidth={2.5} />
                                </div>
                                <div className="font-display text-5xl font-bold">{pantry.length}</div>
                                <div className="text-[color:var(--muted)]">Artikel gelagert</div>
                            </TileLink>
                        );
                    }
                    if (w.widget === "quick_actions") {
                        return (
                            <TileLink key={w.widget + w.order} to="/recipes" testid={`tablet-widget-${w.widget}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="cp-kicker">Rezepte</span>
                                    <BookOpen className="h-7 w-7 text-[color:var(--primary)]" strokeWidth={2.5} />
                                </div>
                                <div className="font-display text-5xl font-bold">{recipes.length}</div>
                            </TileLink>
                        );
                    }
                    return null;
                })}
            </div>
        </div>
    );
}

function TileLink({ to, children, className = "", testid }) {
    return (
        <Link to={to} className={`cp-tablet-tile flex flex-col justify-between ${className}`} data-testid={testid}>
            {children}
        </Link>
    );
}
