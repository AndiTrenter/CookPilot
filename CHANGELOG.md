# Changelog

Alle wichtigen Änderungen an CookPilot werden in dieser Datei dokumentiert.

Format: [Keep a Changelog](https://keepachangelog.com/de/1.1.0/) · SemVer.

## [0.4.0] - 2026-04

### Hinzugefügt
- **lidl-kochen.de Integration**:
  - URL-Import für `www.lidl-kochen.de/rezeptwelt/...` via JSON-LD (`schema.org/Recipe`).
  - **Live-Suche** direkt in `/recipes`: Suchbegriff wird an die offizielle Lidl-DE Such-API (`/search_v2/api/search/recipes`) geschickt und liefert sofort aktuelle Treffer mit Bild, Kochzeit und Beliebtheits-Score. Kombinierte Suche mit dem bestehenden Lidl-CH-Cache.
  - Pro Treffer „In Rezeptbuch"-Button → parst die Detailseite live und speichert komplette Anleitung mit Zutaten, Schritten und Bild.
- **Generischer JSON-LD Importer** als Fallback in `import_from_url` - jede Rezept-Website, die `schema.org/Recipe` einbettet, funktioniert damit automatisch (Chefkoch, Fooby, Kitchen Stories, Lecker, etc.).
- Neuer Endpoint `GET /api/recipes/external/live-search?q=...&source=lidl_kochen`.
- Externer Rezept-Bereich zeigt Quellen-Chip (Lidl CH / Lidl DE) und Likes-Count.

## [0.3.0] - 2026-04

### Hinzugefügt
- **Rezept-Import aus URL** (`POST /api/recipes/import-url`): Füge eine Rezept-URL von `rezepte.lidl.ch` ein → CookPilot lädt die Seite, extrahiert Titel, Zutaten, Schritte, Bild, Kochzeit, Schwierigkeit und speichert sie in dein Rezeptbuch.
- **Externe Rezept-Suche** direkt in `/recipes`: Suchfeld durchsucht sowohl dein eigenes Rezeptbuch als auch den Cache von 36 Rezepten von `rezepte.lidl.ch`. Ein Klick auf "In Rezeptbuch" übernimmt das Rezept samt Zutaten, Schritt-für-Schritt-Anleitung und Bild.
- **Externer Rezept-Index** (`external_recipes` Collection): Admin kann den Index über "Index aktualisieren" oder `POST /api/recipes/external/refresh` neu einlesen.
- Vorschau-Endpoint `POST /api/recipes/preview-url` für Clients, die vor dem Speichern prüfen wollen.
- Rezept-Detail-Seite zeigt jetzt das Hero-Bild und einen "aus rezepte.lidl.ch"-Chip bei importierten Rezepten.

### Behoben
- Bild-URLs auf dem CDN (`cdn.recipes.lidl`) werden jetzt korrekt aus dem `imageInfo`-Payload rekonstruiert (inkl. Timestamp-Suffix) - vorher 404.

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
