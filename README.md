# CookPilot

**CookPilot** ist dein intelligenter Küchen-Assistent - eine eigenständige Docker-Anwendung für Unraid. Sie verwaltet Rezepte, Einkaufslisten, Vorräte und bietet eine KI-gestützte Kochhilfe. CookPilot ist so entworfen, dass sie später von [Aria](https://github.com/OWNER/aria) als externer Fachdienst konsumiert wird.

> **Unabhängig.** CookPilot enthält keinerlei Emergent-Abhängigkeiten und läuft als klassisches Docker-Image.

## Features (v0.1.0)

- 📖 **Rezepte** - anlegen, bearbeiten, kategorisieren, Favoriten, Suche/Filter.
- 🛒 **Einkaufsliste** - Supermarkt-Modus mit riesigen Checkboxen; automatisch befüllt aus Rezepten und Mindestbeständen.
- 🥫 **Vorrat (Pantry)** - Bestand, Mindestbestand, MHD, Lagerort, Warnungen.
- 🤖 **KI-Kochassistent** - OpenAI GPT (API-Key im Admin-Bereich hinterlegen).
- 👥 **Benutzerverwaltung** - Rollen, Einladung per E-Mail-Link.
- 📺 **Küchen-Wandtablet-Modus** - große Kacheln, wenige Klicks.
- 🧩 **Widget-Konfiguration** - Administrator bestimmt, welche Inhalte wo erscheinen.
- 🔗 **Aria-Integration** - SSO-Endpoint, Allergien-Sync (CaseDesk) und Abfragen wie „Wie viel Milch im April 2026?".
- 📸 **Kassenzettel & Produktfotos** (Phase 3 vorbereitet) - Upload vorhanden, Tesseract OCR im Container installiert.

## Deployment auf Unraid

1. MongoDB 4.4 Container installieren (aus Community Applications) - merke dir IP/Port.
2. CookPilot-Container über Community Applications oder die bereitgestellte [`unraid-template.xml`](./unraid-template.xml) hinzufügen.
3. `MONGO_URL`, `JWT_SECRET`, `COOKPILOT_ADMIN_EMAIL`, `COOKPILOT_ADMIN_PASSWORD`, `COOKPILOT_PUBLIC_URL` setzen.
4. Starten → `http://IP:8001` öffnen → mit Admin-Zugang anmelden.

Das Image wird automatisch als `ghcr.io/OWNER/cookpilot:latest` gebaut (siehe `.github/workflows/docker-build.yml`).

## Lokale Entwicklung (ohne Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001

# Frontend
cd frontend
yarn install
yarn start
```

## Aria-Integration

CookPilot exponiert drei Endpunkte für Aria:

| Endpoint | Zweck |
|---|---|
| `POST /api/aria/sso` | Tauscht Aria-User-Context gegen CookPilot-JWT. |
| `POST /api/aria/allergies` | CaseDesk pusht Allergien / Diät. |
| `GET /api/aria/purchases/aggregate` | Aggregate über Einkäufe (Header `X-Aria-Secret`). |

Beispiel-Anfrage von Aria für „Milch im April 2026":

```
GET /api/aria/purchases/aggregate?product=milch&start_date=2026-04-01&end_date=2026-04-30&agg=sum_price
X-Aria-Secret: <shared-secret>
```

## Versionierung

Siehe [`CHANGELOG.md`](./CHANGELOG.md). SemVer.

## Lizenz

MIT.
