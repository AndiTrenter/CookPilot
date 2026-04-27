import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Minus, AlertTriangle, Archive } from "lucide-react";

const emptyItem = { name: "", amount: "", unit: "", min_amount: "", category: "", location: "", mhd: "" };

export default function Pantry() {
    const [items, setItems] = useState([]);
    const [form, setForm] = useState(emptyItem);

    const load = () => api.get("/pantry").then((r) => setItems(r.data));
    useEffect(() => { load(); }, []);

    const add = async (e) => {
        e.preventDefault();
        if (!form.name.trim()) return;
        try {
            await api.post("/pantry", {
                ...form,
                amount: form.amount === "" ? 0 : +form.amount,
                min_amount: form.min_amount === "" ? 0 : +form.min_amount,
                mhd: form.mhd || null,
            });
            setForm(emptyItem);
            load();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Fehler");
        }
    };

    const adjust = async (id, delta) => {
        await api.post(`/pantry/${id}/adjust`, { delta });
        load();
    };

    const del = async (id) => {
        await api.delete(`/pantry/${id}`);
        load();
    };

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-5xl mx-auto">
            <div className="mb-8">
                <div className="cp-kicker mb-2">Vorratskammer</div>
                <h1 className="font-display text-4xl sm:text-5xl font-bold">Vorrat</h1>
                <p className="text-[color:var(--muted)] mt-2">Bestand, Mindestmengen, MHD.</p>
            </div>
            <form onSubmit={add} className="cp-card mb-6">
                <h2 className="font-display text-xl font-bold mb-4">Neuer Eintrag</h2>
                <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
                    <Field label="Artikel" className="col-span-2 sm:col-span-2">
                        <input className="cp-input" placeholder="z.B. Milch" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="pantry-name-input" />
                    </Field>
                    <Field label="Bestand">
                        <input className="cp-input" type="number" min={0} step="0.1" placeholder="Menge" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} data-testid="pantry-amount-input" />
                    </Field>
                    <Field label="Einheit">
                        <input className="cp-input" placeholder="z.B. l, g, Stk" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} data-testid="pantry-unit-input" />
                    </Field>
                    <Field label="Mindestbestand">
                        <input className="cp-input" type="number" min={0} step="0.1" placeholder="0" value={form.min_amount} onChange={(e) => setForm({ ...form, min_amount: e.target.value })} data-testid="pantry-min-input" />
                    </Field>
                    <div className="flex items-end">
                        <button className="cp-btn-primary w-full h-[46px]" data-testid="pantry-add-btn"><Plus className="h-4 w-4" /></button>
                    </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
                    <Field label="Kategorie (optional)">
                        <input className="cp-input" placeholder="z.B. Milchprodukte" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} data-testid="pantry-category-input" />
                    </Field>
                    <Field label="Lagerort (optional)">
                        <input className="cp-input" placeholder="z.B. Kühlschrank" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} data-testid="pantry-location-input" />
                    </Field>
                    <Field label="Mindesthaltbarkeit (optional)">
                        <input className="cp-input" type="date" value={form.mhd} onChange={(e) => setForm({ ...form, mhd: e.target.value })} data-testid="pantry-mhd-input" />
                    </Field>
                </div>
            </form>

            {items.length === 0 ? (
                <div className="cp-card text-center py-16">
                    <Archive className="h-10 w-10 mx-auto text-[color:var(--muted)] mb-4" />
                    <p className="text-[color:var(--muted)]">Vorratskammer leer.</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {items.map((p) => {
                        const low = p.min_amount > 0 && p.amount < p.min_amount;
                        return (
                            <div key={p.id} className={`cp-card flex flex-col sm:flex-row sm:items-center gap-4 ${low ? "border-[color:var(--warning)]" : ""}`} data-testid={`pantry-row-${p.id}`}>
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <div className="font-semibold text-lg">{p.name}</div>
                                        {low && <span className="cp-chip cp-chip-warn"><AlertTriangle className="h-3 w-3 mr-1" /> Niedrig</span>}
                                    </div>
                                    <div className="text-sm text-[color:var(--muted)] mt-1">
                                        {p.category && <>{p.category} · </>}
                                        {p.location && <>{p.location} · </>}
                                        Min: {p.min_amount} {p.unit}
                                        {p.mhd && <> · MHD: {p.mhd}</>}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button onClick={() => adjust(p.id, -1)} className="cp-btn-secondary h-12 w-12 p-0" data-testid={`pantry-minus-${p.id}`}><Minus className="h-5 w-5" /></button>
                                    <div className="w-24 text-center font-display text-2xl font-bold">
                                        {p.amount} <span className="text-sm text-[color:var(--muted)]">{p.unit}</span>
                                    </div>
                                    <button onClick={() => adjust(p.id, 1)} className="cp-btn-secondary h-12 w-12 p-0" data-testid={`pantry-plus-${p.id}`}><Plus className="h-5 w-5" /></button>
                                    <button onClick={() => del(p.id)} className="cp-btn-ghost text-[color:var(--danger)]" data-testid={`pantry-del-${p.id}`}><Trash2 className="h-4 w-4" /></button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

function Field({ label, className = "", children }) {
    return (
        <label className={`flex flex-col gap-1 ${className}`}>
            <span className="text-xs font-semibold uppercase tracking-wider text-[color:var(--muted)]">{label}</span>
            {children}
        </label>
    );
}
