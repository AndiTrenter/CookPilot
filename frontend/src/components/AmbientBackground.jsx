import React, { useEffect, useState } from "react";

/**
 * AmbientBackground - dezentes Hintergrundbild, passend zur Tageszeit.
 *
 *   05:00 - 10:59  Frühstück  (Kaffee, Brot, Eier, Beeren)
 *   11:00 - 13:59  Mittagessen (Bowl, Salat, Gemüse)
 *   14:00 - 16:59  Nachmittag / Snack (Kaffee, Kuchen, Gewürze)
 *   17:00 - 21:59  Abendessen (Pasta, Pizza, Wein, Kerzenlicht)
 *   22:00 - 04:59  Nacht (warme, ruhige Küchenstimmung)
 *
 * Innerhalb jeder Phase rotieren die Bilder stündlich, sodass der Hintergrund
 * zur vollen Stunde sanft auf das nächste Motiv wechselt.
 *
 * Bilder liegen lokal unter /frontend/public/ambient/01.jpg ... 18.jpg.
 */

// Slot definition: { fromHour, toHour, indices } - toHour is exclusive on the
// hour boundary; the night slot wraps around midnight.
const SLOTS = [
    { name: "fruehstueck", from: 5, to: 11, indices: [7, 11, 12, 13, 18] }, // Brot, Avo-Toast, Beeren, Kaffee, Croissant
    { name: "mittag", from: 11, to: 14, indices: [1, 4, 10, 8] },            // Bowl, Gemüse, Salat, Kräuter
    { name: "nachmittag", from: 14, to: 17, indices: [2, 8, 15, 13] },       // Schneidebrett, Kräuter, Kaffee+Kuchen, Kaffee
    { name: "abend", from: 17, to: 22, indices: [3, 5, 6, 9, 14, 16, 17] },  // Pasta, Pfanne, Tomate, Pizza, Wein, Wein-Glas, Kerze
    { name: "nacht", from: 22, to: 5, indices: [17, 14, 5] },                // Kerze, Wein, Pfanne (warm/ruhig)
];

function slotForHour(hour) {
    return SLOTS.find((s) => {
        if (s.from < s.to) return hour >= s.from && hour < s.to;
        return hour >= s.from || hour < s.to; // wraps around midnight
    });
}

function pickIndexForNow() {
    const now = new Date();
    const slot = slotForHour(now.getHours());
    if (!slot) return 1;
    // Rotate stably within the slot per hour
    const hourEpoch = Math.floor(now.getTime() / (60 * 60 * 1000));
    return slot.indices[hourEpoch % slot.indices.length];
}

function urlFor(idx) {
    const n = String(idx).padStart(2, "0");
    return `${process.env.PUBLIC_URL || ""}/ambient/${n}.jpg`;
}

export default function AmbientBackground() {
    const [idx, setIdx] = useState(pickIndexForNow);

    useEffect(() => {
        const now = new Date();
        const nextHour = new Date(now);
        nextHour.setHours(now.getHours() + 1, 0, 5, 0); // +5s Puffer
        const msToNext = nextHour.getTime() - now.getTime();

        let interval;
        const initial = setTimeout(() => {
            setIdx(pickIndexForNow());
            interval = setInterval(() => setIdx(pickIndexForNow()), 60 * 60 * 1000);
        }, msToNext);

        return () => {
            clearTimeout(initial);
            if (interval) clearInterval(interval);
        };
    }, []);

    const photoUrl = urlFor(idx);

    return (
        <div
            aria-hidden="true"
            data-testid="ambient-background"
            className="pointer-events-none fixed inset-0 -z-10 transition-opacity duration-1000"
            style={{
                backgroundImage: `url("${photoUrl}")`,
                backgroundSize: "cover",
                backgroundPosition: "center",
                opacity: 0.15,
            }}
        />
    );
}
