import React, { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { ChevronDown } from "lucide-react";

/**
 * ProductInput - autocomplete input that searches /api/products and
 * pre-selects a default unit when a known product is picked.
 *
 * Free-text entry remains possible: users can type any name; only the
 * default-unit auto-fill happens on selection of a catalog hit.
 *
 * Props:
 *   value, onChange         controlled input value (the product name)
 *   onUnitSelect(unit)      called when a catalog product is selected
 *   placeholder, className, testId, autoFocus
 */
export default function ProductInput({
    value,
    onChange,
    onUnitSelect,
    placeholder = "Artikel",
    className = "",
    testId,
    autoFocus = false,
}) {
    const [suggestions, setSuggestions] = useState([]);
    const [open, setOpen] = useState(false);
    const [highlight, setHighlight] = useState(0);
    const wrapperRef = useRef(null);
    const debounceRef = useRef(null);

    // Debounced search
    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        const q = (value || "").trim();
        if (!q) {
            setSuggestions([]);
            return;
        }
        debounceRef.current = setTimeout(async () => {
            try {
                const { data } = await api.get("/products", { params: { search: q, limit: 8 } });
                setSuggestions(data);
                setHighlight(0);
            } catch {
                setSuggestions([]);
            }
        }, 180);
        return () => debounceRef.current && clearTimeout(debounceRef.current);
    }, [value]);

    // Close on outside click
    useEffect(() => {
        const onDoc = (e) => {
            if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setOpen(false);
        };
        document.addEventListener("mousedown", onDoc);
        return () => document.removeEventListener("mousedown", onDoc);
    }, []);

    const select = (p) => {
        onChange(p.name);
        if (onUnitSelect && p.default_unit) onUnitSelect(p.default_unit);
        setOpen(false);
    };

    const onKey = (e) => {
        if (!open || suggestions.length === 0) return;
        if (e.key === "ArrowDown") {
            e.preventDefault();
            setHighlight((h) => (h + 1) % suggestions.length);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setHighlight((h) => (h - 1 + suggestions.length) % suggestions.length);
        } else if (e.key === "Enter") {
            e.preventDefault();
            select(suggestions[highlight]);
        } else if (e.key === "Escape") {
            setOpen(false);
        }
    };

    return (
        <div ref={wrapperRef} className={`relative ${className}`}>
            <input
                className="cp-input pr-9"
                placeholder={placeholder}
                value={value}
                onChange={(e) => {
                    onChange(e.target.value);
                    setOpen(true);
                }}
                onFocus={() => setOpen(true)}
                onKeyDown={onKey}
                autoComplete="off"
                autoFocus={autoFocus}
                data-testid={testId}
            />
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[color:var(--muted)] pointer-events-none" />
            {open && suggestions.length > 0 && (
                <div
                    className="absolute z-50 left-0 right-0 mt-1 rounded-2xl border border-[color:var(--border)] bg-white shadow-xl max-h-64 overflow-y-auto"
                    data-testid={testId ? `${testId}-suggestions` : undefined}
                >
                    {suggestions.map((p, i) => (
                        <button
                            key={p.id}
                            type="button"
                            onClick={() => select(p)}
                            onMouseEnter={() => setHighlight(i)}
                            className={`w-full text-left px-4 py-2.5 flex items-center justify-between gap-3 transition-colors ${
                                i === highlight ? "bg-[color:var(--surface-2)]" : "hover:bg-[color:var(--surface-2)]"
                            }`}
                            data-testid={testId ? `${testId}-suggestion-${i}` : undefined}
                        >
                            <span className="font-semibold truncate">{p.name}</span>
                            <span className="text-xs text-[color:var(--muted)] shrink-0">
                                {p.default_unit && <span className="cp-chip mr-2">{p.default_unit}</span>}
                                {p.category}
                            </span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
