import React, { useEffect, useState } from "react";

/**
 * AmbientBackground - dezentes, stündlich wechselndes Rezept-/Küchen-Foto
 * als Hintergrund. Sitzt fixed hinter allen Inhalten, ~10% sichtbar.
 *
 * Bilder werden direkt von images.unsplash.com geladen (CDN, frei nutzbar
 * gemäß Unsplash-Lizenz). Die Auswahl rotiert deterministisch pro Stunde,
 * sodass innerhalb derselben Stunde immer dasselbe Bild zu sehen ist und
 * zur vollen Stunde der nächste Schritt erfolgt.
 */

// Kuratierte Auswahl food/kitchen aus Unsplash. Jeder Eintrag ist eine
// stabile Photo-ID; die Datei wird über images.unsplash.com optimiert.
const PHOTO_IDS = [
    "1546069901-ba9599a7e63c", // bunte Bowl
    "1504674900247-0877df9cc836", // Holzbrett & Gewürze
    "1495521821757-a1efb6729352", // Pasta
    "1490645935967-10de6ba17061", // Gemüseauslage
    "1556909114-f6e7ad7d3136", // Pfanne / kochen
    "1490818387583-1baba5e638af", // Tomate / Olivenöl
    "1542010589005-d1eacc3918f2", // Brot, Mehl
    "1466637574441-749b8f19452f", // Kräuter
    "1565299624946-b28f40a0ae38", // Pizza rustic
    "1512621776951-a57141f2eefd", // Salat
    "1473093295043-cdd812d0e601", // Avocado-Toast
    "1519996409144-56c88c9aa612", // Beeren
];

function urlFor(id) {
    return `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=1920&q=70`;
}

function pickIndexForNow() {
    // Stunden seit Unix-Epoch → mod Anzahl Bilder
    const hour = Math.floor(Date.now() / (60 * 60 * 1000));
    return hour % PHOTO_IDS.length;
}

export default function AmbientBackground() {
    const [idx, setIdx] = useState(pickIndexForNow);

    useEffect(() => {
        // Berechne Millisekunden bis zur nächsten vollen Stunde
        const now = new Date();
        const nextHour = new Date(now);
        nextHour.setHours(now.getHours() + 1, 0, 5, 0); // +5s Puffer
        const msToNext = nextHour.getTime() - now.getTime();

        const initial = setTimeout(() => {
            setIdx(pickIndexForNow());
            // Danach jede Stunde
            const interval = setInterval(() => setIdx(pickIndexForNow()), 60 * 60 * 1000);
            // Cleanup für interval per Closure
            return () => clearInterval(interval);
        }, msToNext);

        return () => clearTimeout(initial);
    }, []);

    const photoUrl = urlFor(PHOTO_IDS[idx]);

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
