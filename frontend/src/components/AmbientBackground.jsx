import React, { useEffect, useState } from "react";

/**
 * AmbientBackground - dezentes, stündlich wechselndes Rezept-/Küchen-Foto
 * im Hintergrund. Sitzt fixed hinter allen Inhalten, ~10% sichtbar.
 *
 * Die Bilder liegen lokal in /frontend/public/ambient/. So funktioniert der
 * Effekt offline, hinter Privacy-Blockern und ohne externe CDN-Abhängigkeit.
 *
 * Die Auswahl rotiert deterministisch pro Stunde, sodass innerhalb derselben
 * Stunde immer dasselbe Bild zu sehen ist und zur vollen Stunde der Wechsel
 * mit einer sanften Fade-Animation erfolgt.
 */

const TOTAL_PHOTOS = 12;

function urlFor(idx) {
    const n = String(idx + 1).padStart(2, "0");
    return `${process.env.PUBLIC_URL || ""}/ambient/${n}.jpg`;
}

function pickIndexForNow() {
    const hour = Math.floor(Date.now() / (60 * 60 * 1000));
    return hour % TOTAL_PHOTOS;
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
                opacity: 0.1,
            }}
        />
    );
}
