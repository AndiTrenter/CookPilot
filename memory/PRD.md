# CookPilot - PRD & Projekt-Memory

## Original Problem Statement (Kurzfassung)
CookPilot ist ein eigenständiger Küchen-Agent als Docker-Anwendung für Unraid. Er soll über GitHub entwickelt, versioniert und langfristig erweitert werden. Die Integration in Aria (zentrales Dashboard) macht ein anderer Entwickler - CookPilot liefert die fachliche API.

Vollständige Anforderungen siehe `docs/lastenheft.md` (bzw. initiales User-Prompt).

## Nutzer-Entscheidungen (vom Nutzer bestätigt)
1. **KI:** OpenAI GPT-5.2 via Admin-Panel (API-Key wird in MongoDB gespeichert, NICHT über env).
2. **Auth:** JWT-Login + E-Mail-Invite (Admin lädt ein). Aria-SSO über Shared-Secret (in Admin-Panel konfigurierbar). Rechte in Aria steuern, ob CookPilot sichtbar ist.
3. **CI/CD:** Vollständiges GitHub-Workflow + `Dockerfile` + `docker-compose.yml` + `unraid-template.xml`.
4. **DB:** MongoDB 4.4 (wegen Unraid-Server).
5. **OCR:** Tesseract lokal (im Docker installiert); nur Upload + Hook für Phase 3 vorbereitet. Ziel: (a) Einkaufsliste-Supermarkt-Check-Off, (b) Daheim beim Einräumen Produktfotos → automatisches Abhaken + MHD + Preis aus Kassenzettel. Daten sollen von Aria/CaseDesk abfragbar sein (z. B. "Milch im April 2026").

## Architektur
- Backend: FastAPI (Python 3.11), direkte OpenAI SDK (NO emergentintegrations).
- Frontend: React 19 + Tailwind + Shadcn/UI, eigenes "Organic Utility"-Theme (Terracotta `#C8553D` auf Sand `#FAF8F5`, Cabinet Grotesk + Manrope).
- Datenbank: MongoDB 4.4.
- Deployment: Single Docker Image (Stage 1 baut React statisch, Stage 2 Python-Runtime serviert SPA + API). `docker-compose.yml` für lokale Tests, `unraid-template.xml` für Community Applications.
- Versionierung: `VERSION` (0.1.0), `CHANGELOG.md`, SemVer, GitHub Actions (`ghcr.io/OWNER/cookpilot`).

## Was in Phase 3 Kickoff implementiert wurde (stand 2026-04-24, v0.2.0)
- **Backend NEW** `/app/backend/vision_service.py` und `/app/backend/routers/vision_router.py` mit 4 Endpoints:
  - `POST /api/vision/scan-products` (1-6 Bilder) → OpenAI Vision erkennt Name/Marke/MHD/Menge/Confidence + matched shopping-item pro Produkt.
  - `POST /api/vision/apply-scan` → hakt Einkaufsliste ab + legt Vorrat mit MHD an.
  - `POST /api/vision/parse-receipt` → OpenAI Vision erkennt Store, Datum, Posten mit Preisen.
  - `POST /api/vision/apply-receipt` → persistiert als `purchases` + hakt Einkaufsliste ab + markiert receipt applied=true.
- **Admin-Einstellung** `vision_model` (Default `gpt-4o`) - separat konfigurierbar vom Chat-Modell.
- **Frontend NEW** `/scan` und `/receipt-scan` Routen mit Multi-Photo-Upload, Review-Karten, mobiler Kamera-Integration.
- Dashboard-Quick-Actions „Einkauf einräumen" und „Kassenzettel".
- Emergent-Branding vollständig entfernt (kein Badge, kein PostHog, kein visual-edits dep).
- Version bump 0.1.0 → 0.2.0 in `VERSION`, `CHANGELOG.md`, `backend/.env`.
- Testing: 31/31 Backend-Tests, Frontend-Smoke via Playwright ✅.

## Was in Phase 1 implementiert wurde (stand 2026-04-24)
- Backend-Module (/app/backend/):
- Backend-Module (/app/backend/):
  - `server.py` - FastAPI Entry + SPA-Serve + Lifespan mit Seed-Admin.
  - `db.py`, `models.py`, `auth.py` (JWT + bcrypt), `seed.py`, `llm_service.py`, `email_service.py`.
  - Routers in `/app/backend/routers/`: auth, users, invites, recipes, shopping, pantry, chat, settings, widgets, aria, receipts + purchases.
- Aria-Integration (fachlich nutzbar):
  - `POST /api/aria/sso` - tauscht externe User-Kontextdaten gegen JWT (auto-User-Create).
  - `POST /api/aria/allergies` - CaseDesk pusht Allergien/Diät → fließt in KI-Kochhilfe ein.
  - `GET /api/aria/purchases/aggregate?product=...&start_date=...&end_date=...` (Header `X-Aria-Secret`) - Abfragen wie "Milch im April 2026".
- Frontend-Routen:
  - `/login`, `/invite/:token`, `/` Dashboard, `/recipes`, `/recipes/new`, `/recipes/:id`, `/recipes/:id/edit`, `/recipes/:id/cook`, `/shopping`, `/pantry`, `/chat`, `/tablet`, `/admin`.
- Admin-Panel mit Tabs: Benutzer · Einladungen · KI (OpenAI-Key) · SMTP · Aria (Shared-Secret) · Widgets-Dashboard · Widgets-Tablet.
- Küchen-Wandtablet-Modus unter `/tablet` (Bento-Layout, konfigurierbar).
- Kassenzettel-Upload: `POST /api/receipts/upload` (persistiert in /data/uploads), OCR-Hook `POST /api/receipts/{id}/ocr` (Tesseract).
- Purchases-Collection + CRUD unter `/api/purchases` (nach Phase 3 erweiterbar).

## Deferred / Backlog (P0 → P2)
### P0 (nächste Phase 2 - Komfort)
- [ ] Rezeptvorschläge aus Vorrat (Backend-Endpoint + UI).
- [ ] Wochenplan (Backend-Model + UI).
- [ ] Rezeptbilder Upload (im Admin-Panel).
### P1 (Phase 3 - OCR / Fotos)
- [ ] Produktfoto-Erkennung im Supermarkt (OpenAI Vision) mit Einkaufs-Abgleich und MHD-Erkennung.
- [ ] Kassenzettel-OCR + Produktzuordnung → Purchases speichern.
- [ ] Mustererkennung von Kaufverhalten ("Milch alle 5-7 Tage").
### P2 (Phase 4 - KI-Ausbau)
- [ ] Ollama-Adapter (lokale LLM).
- [ ] Sprachsteuerung.
- [ ] Smart-Home-Anbindung.

## Testing-Stand (2026-04-24)
- Login-Seite & Dashboard visuell verifiziert (Playwright Screenshots).
- Backend-Health-Endpoint + `/api/auth/login` per curl getestet (200 OK, JWT zurück).
- Testing-Subagent wurde noch nicht aufgerufen. Beim nächsten Schritt mandatory.

## Credentials
Siehe `/app/memory/test_credentials.md`.
