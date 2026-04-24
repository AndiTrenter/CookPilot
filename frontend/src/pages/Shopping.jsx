import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Plus, Trash2, ShoppingCart, CheckCheck, AlertTriangle } from "lucide-react";

export default function Shopping() {
    const [items, setItems] = useState([]);
    const [name, setName] = useState("");
    const [amount, setAmount] = useState(1);
    const [unit, setUnit] = useState("");

    const load = () => api.get("/shopping").then((r) => setItems(r.data));
    useEffect(() => { load(); }, []);

    const add = async (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        await api.post("/shopping", { name, amount: +amount, unit });
        setName(""); setAmount(1); setUnit("");
        load();
    };

    const toggle = async (id) => {
        await api.post(`/shopping/${id}/toggle`);
        load();
    };

    const del = async (id) => {
        await api.delete(`/shopping/${id}`);
        load();
    };

    const clearChecked = async () => {
        if (!window.confirm("Alle abgehakten Artikel entfernen?")) return;
        const { data } = await api.post("/shopping/clear-checked");
        toast.success(`${data.deleted} Artikel entfernt`);
        load();
    };

    const addFromLowStock = async () => {
        const { data } = await api.post("/shopping/from-low-stock");
        toast.success(`${data.added} Artikel ergänzt`);
        load();
    };

    const open = items.filter((i) => !i.checked);
    const done = items.filter((i) => i.checked);

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-3xl mx-auto">
            <div className="mb-8">
                <div className="cp-kicker mb-2">Supermarkt-Modus</div>
                <h1 className="font-display text-4xl sm:text-5xl font-bold">Einkaufsliste</h1>
                <p className="text-[color:var(--muted)] mt-2">{open.length} offen · {done.length} erledigt</p>
            </div>

            <form onSubmit={add} className="cp-card mb-6">
                <div className="grid grid-cols-12 gap-2">
                    <input className="cp-input col-span-6 sm:col-span-7" placeholder="Artikel" value={name} onChange={(e) => setName(e.target.value)} data-testid="shopping-name-input" />
                    <input className="cp-input col-span-2" type="number" min={0} step="0.1" value={amount} onChange={(e) => setAmount(e.target.value)} data-testid="shopping-amount-input" />
                    <input className="cp-input col-span-2" placeholder="Einheit" value={unit} onChange={(e) => setUnit(e.target.value)} data-testid="shopping-unit-input" />
                    <button className="cp-btn-primary col-span-2" data-testid="shopping-add-btn">
                        <Plus className="h-4 w-4" />
                    </button>
                </div>
                <div className="flex flex-wrap gap-2 mt-4">
                    <button type="button" onClick={addFromLowStock} className="cp-btn-secondary" data-testid="shopping-from-lowstock-btn">
                        <AlertTriangle className="h-4 w-4" /> Aus Vorrats-Mindestbestand
                    </button>
                    <button type="button" onClick={clearChecked} className="cp-btn-ghost" data-testid="shopping-clear-checked-btn">
                        <CheckCheck className="h-4 w-4" /> Erledigte entfernen
                    </button>
                </div>
            </form>

            {items.length === 0 ? (
                <div className="cp-card text-center py-16">
                    <ShoppingCart className="h-10 w-10 mx-auto text-[color:var(--muted)] mb-4" />
                    <p className="text-[color:var(--muted)]">Noch nichts auf der Liste.</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {open.map((i) => (
                        <Row key={i.id} item={i} onToggle={toggle} onDelete={del} />
                    ))}
                    {done.length > 0 && (
                        <>
                            <div className="cp-kicker mt-8 mb-2">Erledigt</div>
                            {done.map((i) => (
                                <Row key={i.id} item={i} onToggle={toggle} onDelete={del} />
                            ))}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

function Row({ item, onToggle, onDelete }) {
    return (
        <div className="cp-shop-row" data-checked={item.checked ? "true" : "false"} data-testid={`shop-row-${item.id}`}>
            <button
                onClick={() => onToggle(item.id)}
                data-testid={`shop-toggle-${item.id}`}
                className={`h-14 w-14 rounded-2xl border-2 flex items-center justify-center transition-colors shrink-0 ${
                    item.checked ? "bg-[color:var(--primary)] border-[color:var(--primary)]" : "bg-white border-[color:var(--border)]"
                }`}
                aria-pressed={item.checked}
            >
                {item.checked && (
                    <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="h-8 w-8">
                        <path d="M5 12l5 5L20 7" />
                    </svg>
                )}
            </button>
            <div className="flex-1 min-w-0">
                <div className="cp-shop-name text-xl sm:text-lg font-semibold truncate">{item.name}</div>
                <div className="text-sm text-[color:var(--muted)]">
                    {item.amount} {item.unit} {item.source && item.source !== "manuell" ? `· ${item.source.split(":")[0]}` : ""}
                </div>
            </div>
            <button onClick={() => onDelete(item.id)} className="cp-btn-ghost text-[color:var(--danger)]" data-testid={`shop-del-${item.id}`}>
                <Trash2 className="h-5 w-5" />
            </button>
        </div>
    );
}
