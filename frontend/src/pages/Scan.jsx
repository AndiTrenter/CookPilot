import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Camera, Upload, Sparkles, ChevronLeft, Check, Loader2, Trash2 } from "lucide-react";

export default function Scan() {
    const fileRef = useRef(null);
    const [files, setFiles] = useState([]); // File objects
    const [previews, setPreviews] = useState([]); // data URLs
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null); // { products: [...] }
    const [applying, setApplying] = useState(false);

    const addFiles = (incoming) => {
        const list = Array.from(incoming || []).slice(0, 6 - files.length);
        if (!list.length) return;
        setFiles((prev) => [...prev, ...list]);
        list.forEach((f) => {
            const reader = new FileReader();
            reader.onload = (e) => setPreviews((p) => [...p, e.target.result]);
            reader.readAsDataURL(f);
        });
    };

    const removeAt = (i) => {
        setFiles((f) => f.filter((_, idx) => idx !== i));
        setPreviews((p) => p.filter((_, idx) => idx !== i));
    };

    const scan = async () => {
        if (files.length === 0) return;
        setLoading(true);
        const form = new FormData();
        files.forEach((f) => form.append("files", f));
        try {
            const { data } = await api.post("/vision/scan-products", form, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            // annotate selectable defaults
            const enriched = data.products.map((p) => ({
                ...p,
                matched_shopping_id: p.suggested_shopping_id || null,
                add_to_pantry: true,
                keep: true,
            }));
            setResult({ ...data, products: enriched });
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Vision-Fehler");
        } finally {
            setLoading(false);
        }
    };

    const toggleKeep = (i) => setResult((r) => ({ ...r, products: r.products.map((p, idx) => idx === i ? { ...p, keep: !p.keep } : p) }));
    const setField = (i, field, value) => setResult((r) => ({ ...r, products: r.products.map((p, idx) => idx === i ? { ...p, [field]: value } : p) }));

    const apply = async () => {
        if (!result) return;
        const items = result.products.filter((p) => p.keep).map((p) => ({
            name: p.name,
            brand: p.brand,
            mhd: p.mhd,
            quantity: p.quantity,
            unit: p.unit,
            matched_shopping_id: p.matched_shopping_id || null,
            add_to_pantry: !!p.add_to_pantry,
        }));
        setApplying(true);
        try {
            const { data } = await api.post("/vision/apply-scan", { items });
            toast.success(`${data.shopping_ticked} Einkaufs-Artikel abgehakt · ${data.pantry_added} im Vorrat`);
            setFiles([]); setPreviews([]); setResult(null);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Fehler");
        } finally {
            setApplying(false);
        }
    };

    return (
        <div className="px-4 sm:px-8 lg:px-12 py-6 sm:py-12 max-w-5xl mx-auto">
            <div className="flex items-center gap-3 mb-2">
                <Link to="/shopping" className="cp-btn-ghost" data-testid="scan-back-btn"><ChevronLeft className="h-4 w-4" /> Zurück</Link>
            </div>
            <div className="mb-8">
                <div className="cp-kicker mb-2">Foto-Erkennung · Einkauf einräumen</div>
                <h1 className="font-display text-4xl sm:text-5xl font-bold">Produkte scannen</h1>
                <p className="text-[color:var(--muted)] mt-2">Fotografiere 1-6 Produkte. CookPilot erkennt Name und MHD, hakt die Einkaufsliste ab und legt Vorrat an.</p>
            </div>

            {!result && (
                <>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mb-6">
                        {previews.map((src, i) => (
                            <div key={i} className="relative aspect-square rounded-2xl overflow-hidden border border-[color:var(--border)]" data-testid={`scan-preview-${i}`}>
                                <img src={src} alt="" className="w-full h-full object-cover" />
                                <button onClick={() => removeAt(i)} className="absolute top-2 right-2 h-9 w-9 rounded-full bg-black/60 text-white flex items-center justify-center" data-testid={`scan-remove-${i}`}>
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        ))}
                        {files.length < 6 && (
                            <button
                                onClick={() => fileRef.current?.click()}
                                className="aspect-square rounded-2xl border-2 border-dashed border-[color:var(--border)] bg-white flex flex-col items-center justify-center gap-2 text-[color:var(--muted)] hover:border-[color:var(--primary)] hover:text-[color:var(--primary)]"
                                data-testid="scan-add-photo-btn"
                            >
                                <Camera className="h-8 w-8" strokeWidth={2} />
                                <span className="text-sm font-semibold">Foto hinzufügen</span>
                            </button>
                        )}
                    </div>

                    <input
                        ref={fileRef}
                        type="file"
                        accept="image/*"
                        capture="environment"
                        multiple
                        className="hidden"
                        onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
                        data-testid="scan-file-input"
                    />

                    <div className="flex gap-3">
                        <button onClick={() => fileRef.current?.click()} className="cp-btn-secondary" data-testid="scan-upload-btn">
                            <Upload className="h-4 w-4" /> Dateien wählen
                        </button>
                        <button onClick={scan} disabled={files.length === 0 || loading} className="cp-btn-primary flex-1" data-testid="scan-analyze-btn">
                            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Sparkles className="h-5 w-5" />}
                            {loading ? "Analysiere…" : `${files.length} Foto${files.length === 1 ? "" : "s"} analysieren`}
                        </button>
                    </div>
                </>
            )}

            {result && (
                <div className="space-y-4">
                    <div className="cp-card">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="font-display text-2xl font-bold">{result.products.length} Produkt{result.products.length === 1 ? "" : "e"} erkannt</h2>
                            <button onClick={() => setResult(null)} className="cp-btn-ghost" data-testid="scan-reset-btn">Zurücksetzen</button>
                        </div>
                        {result.products.length === 0 && (
                            <p className="text-[color:var(--muted)]">Leider konnte CookPilot nichts erkennen. Versuche es mit besserem Licht oder näheren Fotos.</p>
                        )}
                        <div className="space-y-3">
                            {result.products.map((p, i) => (
                                <div key={i} className={`rounded-2xl border p-4 ${p.keep ? "border-[color:var(--border)] bg-white" : "border-[color:var(--border)] bg-[color:var(--surface-2)] opacity-60"}`} data-testid={`scan-product-${i}`}>
                                    <div className="flex items-start justify-between gap-3 mb-3">
                                        <div className="flex-1">
                                            <input
                                                className="cp-input mb-2"
                                                value={p.name}
                                                onChange={(e) => setField(i, "name", e.target.value)}
                                                data-testid={`scan-product-name-${i}`}
                                            />
                                            <div className="flex flex-wrap gap-2 text-xs text-[color:var(--muted)]">
                                                {p.brand && <span className="cp-chip">{p.brand}</span>}
                                                <span className="cp-chip">{Math.round((p.confidence || 0) * 100)}% Treffer</span>
                                            </div>
                                        </div>
                                        <button onClick={() => toggleKeep(i)} className="cp-btn-ghost text-[color:var(--danger)]" data-testid={`scan-drop-${i}`}>
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    </div>
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                        <div>
                                            <label className="cp-label">Menge</label>
                                            <input type="number" step="0.1" className="cp-input" value={p.quantity || 0} onChange={(e) => setField(i, "quantity", +e.target.value)} data-testid={`scan-qty-${i}`} />
                                        </div>
                                        <div>
                                            <label className="cp-label">Einheit</label>
                                            <input className="cp-input" value={p.unit || ""} onChange={(e) => setField(i, "unit", e.target.value)} data-testid={`scan-unit-${i}`} />
                                        </div>
                                        <div className="col-span-2">
                                            <label className="cp-label">MHD</label>
                                            <input type="date" className="cp-input" value={p.mhd || ""} onChange={(e) => setField(i, "mhd", e.target.value)} data-testid={`scan-mhd-${i}`} />
                                        </div>
                                    </div>
                                    <div className="flex flex-wrap gap-3 mt-3 text-sm">
                                        <label className="flex items-center gap-2">
                                            <input type="checkbox" checked={!!p.matched_shopping_id} onChange={(e) => setField(i, "matched_shopping_id", e.target.checked ? (p.suggested_shopping_id || null) : null)} data-testid={`scan-ticksop-${i}`} />
                                            Einkaufsliste abhaken {p.suggested_shopping_id ? <span className="cp-chip cp-chip-ok">Match</span> : <span className="cp-chip">kein Match</span>}
                                        </label>
                                        <label className="flex items-center gap-2">
                                            <input type="checkbox" checked={!!p.add_to_pantry} onChange={(e) => setField(i, "add_to_pantry", e.target.checked)} data-testid={`scan-addpantry-${i}`} />
                                            In Vorrat eintragen
                                        </label>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {result.products.length > 0 && (
                        <button onClick={apply} disabled={applying} className="cp-btn-primary w-full" data-testid="scan-apply-btn">
                            {applying ? <Loader2 className="h-5 w-5 animate-spin" /> : <Check className="h-5 w-5" />}
                            Übernehmen
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
