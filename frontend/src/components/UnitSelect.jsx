import React, { useEffect, useState } from "react";
import { api } from "../lib/api";

let cachedUnits = null;

export default function UnitSelect({ value, onChange, allowEmpty = true, className = "", testId }) {
    const [units, setUnits] = useState(cachedUnits || []);

    useEffect(() => {
        if (cachedUnits) return;
        api.get("/products/units")
            .then((r) => {
                cachedUnits = r.data.units || [];
                setUnits(cachedUnits);
            })
            .catch(() => setUnits([]));
    }, []);

    return (
        <select
            className={`cp-input ${className}`}
            value={value || ""}
            onChange={(e) => onChange(e.target.value)}
            data-testid={testId}
        >
            {allowEmpty && <option value="">Einheit…</option>}
            {units.map((u) => (
                <option key={u} value={u}>{u}</option>
            ))}
            {value && !units.includes(value) && (
                <option value={value}>{value} (eigene)</option>
            )}
        </select>
    );
}
