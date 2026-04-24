import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Camera, Upload, Receipt, ChevronLeft, Check, Loader2, Trash2 } from "lucide-react";

export default function ReceiptScan() {
    const fileRef = useRef(null);
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [applying, setApplying] = useState(false);

    const pickFile = (f) => {
        if (!f) return;
        setFile(f);
        const reader = new FileReader();
        reader.onload = (e) => setPreview(e.target.result);
        reader.readAsDataURL(f);
    };

    const parse = async () => {
        if (!file) return;
        setLoading(true);
        const form = new FormData();
        form.append("file", file);
        try {
            const { data } = await api.post("/vision/parse-receipt", form, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            const enriched = {
                ...data,
                items: data.items.map((it) => ({
                    ...it,
                    matched_shopping_id: it.suggested_shopping_id || null,
                    keep: true,
                })),
            };
            setResult(enriched);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Vision-Fehler");
        } finally {
            setLoading(false);
        }
    };

    const setItem = (i, field, value) => setResult((r) => ({ ...r, items: r.items.map((it, idx) => idx === i ? { ...it, [field]: value } : it) }));
    const toggleKeep = (i) => setItem(i, "keep", !result.items[i].keep);

    const apply = async () => {
        if (!result) return;
        const items = result.items.filter((i) => i.keep).map((i) => ({
            product_name: i.product_name,
            product_key: i.product_key || i.product_name.toLowerCase(),
            quantity: +i.quantity || 1,
            unit: i.unit || "",
            price_cents: +i.price_cents || 0,
            matched_shopping_id: i.matched_shopping_id || null,
        }));
        setApplying(true);
        try {
            const { data } = await api.post("/vision/apply-receipt", {
                receipt_id: result.receipt_id,
                store: result.store,
                purchase_date: result.purchase_date || new Date().toISOString().slice(0, 10),
                items,
            });
            toast.success(`${data.purchases_added} Einkäufe erfasst · ${data.shopping_ticked} abgehakt`);
            setFile(null); setPreview(null); setResult(null);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Fehler");
        } finally {
            setApplying(false);
        }
    };

    const totalCents = (result?.items || []).filter((i) => i.keep).reduce((s, i) => s + (+i.price_cents || 0), 0);

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-4xl mx-auto">
            <div className="flex items-center gap-3 mb-2">
                <Link to="/shopping" className="cp-btn-ghost" data-testid="receipt-back-btn"><ChevronLeft className="h-4 w-4" /> Zurück</Link>
            </div>
            <div className="mb-8">
                <div className="cp-kicker mb-2">Foto-Erkennung · Kassenzettel</div>
                <h1 className="font-display text-4xl sm:text-5xl font-bold">Kassenzettel scannen</h1>
                <p className="text-[color:var(--muted)] mt-2">Fotografiere deinen Kassenzettel. CookPilot liest Produkte und Preise aus, vergleicht mit deiner Einkaufsliste und speichert die Einkaufshistorie für Auswertungen.</p>
            </div>

            {!result && (
                <>
                    <div className="cp-card mb-6">
                        {preview ? (
                            <div className="relative">
                                <img src={preview} alt="" className="w-full max-h-[480px] object-contain rounded-2xl" />
                                <button onClick={() => { setFile(null); setPreview(null); }} className="absolute top-3 right-3 h-10 w-10 rounded-full bg-black/60 text-white flex items-center justify-center" data-testid="receipt-reset-btn">
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        ) : (
                            <button
                                onClick={() => fileRef.current?.click()}
                                className="w-full aspect-[3/4] sm:aspect-[16/9] rounded-2xl border-2 border-dashed border-[color:var(--border)] flex flex-col items-center justify-center gap-3 text-[color:var(--muted)] hover:border-[color:var(--primary)] hover:text-[color:var(--primary)]"
                                data-testid="receipt-pick-btn"
                            >
                                <Receipt className="h-12 w-12" strokeWidth={2} />
                                <span className="font-semibold">Kassenzettel fotografieren oder hochladen</span>
                            </button>
                        )}
                    </div>

                    <input
                        ref={fileRef}
                        type="file"
                        accept="image/*"
                        capture="environment"
                        className="hidden"
                        onChange={(e) => { pickFile(e.target.files?.[0]); e.target.value = ""; }}
                        data-testid="receipt-file-input"
                    />

                    <div className="flex gap-3">
                        <button onClick={() => fileRef.current?.click()} className="cp-btn-secondary" data-testid="receipt-upload-btn">
                            <Upload className="h-4 w-4" /> Datei wählen
                        </button>
                        <button onClick={parse} disabled={!file || loading} className="cp-btn-primary flex-1" data-testid="receipt-parse-btn">
                            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Camera className="h-5 w-5" />}
                            {loading ? "Analysiere…" : "Kassenzettel lesen"}
                        </button>
                    </div>
                </>
            )}

            {result && (
                <div className="space-y-4">
                    <div className="cp-card">
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-5">
                            <div>
                                <label className="cp-label">Geschäft</label>
                                <input className="cp-input" value={result.store || ""} onChange={(e) => setResult({ ...result, store: e.target.value })} data-testid="receipt-store-input" />
                            </div>
                            <div>
                                <label className="cp-label">Datum</label>
                                <input type="date" className="cp-input" value={result.purchase_date || ""} onChange={(e) => setResult({ ...result, purchase_date: e.target.value })} data-testid="receipt-date-input" />
                            </div>
                            <div>
                                <label className="cp-label">Summe</label>
                                <div className="font-display text-3xl font-bold">{(totalCents / 100).toFixed(2)} €</div>
                            </div>
                        </div>

                        <div className="flex items-center justify-between mb-3">
                            <h2 className="font-display text-2xl font-bold">Posten ({result.items.length})</h2>
                            <button onClick={() => setResult(null)} className="cp-btn-ghost" data-testid="receipt-redo-btn">Nochmal scannen</button>
                        </div>

                        <div className="space-y-2">
                            {result.items.map((it, i) => (
                                <div key={i} className={`rounded-2xl border p-3 ${it.keep ? "bg-white border-[color:var(--border)]" : "bg-[color:var(--surface-2)] opacity-60 border-[color:var(--border)]"}`} data-testid={`receipt-item-${i}`}>
                                    <div className="grid grid-cols-12 gap-2 items-center">
                                        <input className="cp-input col-span-12 sm:col-span-5" value={it.product_name} onChange={(e) => setItem(i, "product_name", e.target.value)} data-testid={`receipt-item-name-${i}`} />
                                        <input className="cp-input col-span-3 sm:col-span-2" type="number" step="0.01" value={it.quantity} onChange={(e) => setItem(i, "quantity", +e.target.value)} data-testid={`receipt-item-qty-${i}`} />
                                        <input className="cp-input col-span-3 sm:col-span-2" placeholder="Einh." value={it.unit} onChange={(e) => setItem(i, "unit", e.target.value)} data-testid={`receipt-item-unit-${i}`} />
                                        <input className="cp-input col-span-4 sm:col-span-2" type="number" step="1" value={it.price_cents} onChange={(e) => setItem(i, "price_cents", +e.target.value)} data-testid={`receipt-item-price-${i}`} />
                                        <button onClick={() => toggleKeep(i)} className="cp-btn-ghost text-[color:var(--danger)] col-span-2 sm:col-span-1" data-testid={`receipt-item-drop-${i}`}>
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    </div>
                                    <div className="mt-2 flex items-center gap-2 text-sm">
                                        <input type="checkbox" checked={!!it.matched_shopping_id} onChange={(e) => setItem(i, "matched_shopping_id", e.target.checked ? (it.suggested_shopping_id || null) : null)} data-testid={`receipt-match-${i}`} />
                                        <span className="text-[color:var(--muted)]">
                                            Einkaufsliste abhaken
                                            {it.suggested_shopping_id ? <span className="cp-chip cp-chip-ok ml-2">Match</span> : <span className="cp-chip ml-2">kein Match</span>}
                                        </span>
                                        <span className="ml-auto text-[color:var(--muted)]">{(it.price_cents / 100).toFixed(2)} €</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <button onClick={apply} disabled={applying} className="cp-btn-primary w-full" data-testid="receipt-apply-btn">
                        {applying ? <Loader2 className="h-5 w-5 animate-spin" /> : <Check className="h-5 w-5" />}
                        Einkauf speichern
                    </button>
                </div>
            )}
        </div>
    );
}
