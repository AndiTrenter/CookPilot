# Changelog

Alle wichtigen Änderungen an CookPilot werden in dieser Datei dokumentiert.

Format: [Keep a Changelog](https://keepachangelog.com/de/1.1.0/) · SemVer.

## [0.2.0] - 2026-04

### Hinzugefügt (Phase 3 Kickoff)
- **Foto-Erkennung für Einkauf** (`/scan`): 1-6 Produktfotos → OpenAI Vision erkennt Name, Marke, MHD, Menge → automatischer Abgleich mit offenen Einkaufs-Artikeln → Einkaufsliste wird abgehakt und Vorrat mit MHD befüllt (mit Review-Schritt).
- **Kassenzettel-Erkennung** (`/receipt-scan`): ein Foto → OpenAI Vision extrahiert Store, Datum, Posten mit Preisen → Review → Einträge landen in `purchases`-Collection → direkt abfragbar über `/api/aria/purchases/aggregate`.
- Neue Backend-Endpoints: `POST /api/vision/scan-products`, `POST /api/vision/apply-scan`, `POST /api/vision/parse-receipt`, `POST /api/vision/apply-receipt`.
- Admin-Einstellung: getrenntes **Vision-Modell** (Default `gpt-4o`).
- Dashboard-Schnellzugriffe: „Einkauf einräumen" und „Kassenzettel".
- „Made with Emergent"-Badge + emergentbase/visual-edits Dependency komplett entfernt - App ist jetzt vollständig Emergent-frei.

## [0.1.0] - 2026-02

### Hinzugefügt
- Eigenständiger Docker-Container, lauffähig auf Unraid.
- Rezeptverwaltung (CRUD, Kategorien, Zutaten, Schritte, Favoriten, Suche/Filter).
- Einkaufsliste inkl. Supermarkt-Modus (große Checkboxen) und Übernahme aus Rezepten / Mindestbeständen.
- Vorratsverwaltung (Pantry) mit Mindestbestand, MHD, Lagerort und Warnungen.
- KI-Kochassistent (OpenAI GPT-5.2, API-Key im Admin-Bereich hinterlegbar).
- Benutzerverwaltung mit Rollen (Admin / User) und E-Mail-Einladung über SMTP.
- Konfigurierbare Widgets für das Standard-Dashboard und den Küchen-Wandtablet-Modus.
- Aria-Integrationsschicht:
  - `POST /api/aria/sso` (JWT-Handoff anhand Aria `external_id`)
  - `POST /api/aria/allergies` (CaseDesk pusht Allergien/Diät)
  - `GET /api/aria/purchases/aggregate` (Abfragen wie „Milch im April 2026")
- Vorbereitung für Phase 3: Kassenzettel-Upload, OCR-Hook (Tesseract, deu), `purchases`-Collection.
- GitHub Action: Build & Publish nach `ghcr.io`.
- Unraid Community Applications Template (`unraid-template.xml`).
