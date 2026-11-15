> **AgroMatch v3 (Kazakhstan + global):** improved field geometry, source-labelled map point conditions, reliable weather refresh, RU/EN navigation, and regression tests. [Implementation roadmap](AGROMATCH_ROADMAP.md). Render Free still uses *temporary SQLite storage*; do not treat it as a persistent farm database.

> **New:** NASA daily numeric indicators, validated AppEEARS source selection and optional SRTM mirror elevation. See [NASA_INTEGRATION.md](NASA_INTEGRATION.md) for supported sources and limitations.

# AgroMatch — NASA Earth Intelligence × Farmer Network

AgroMatch combines satellite and climate information, rule-based agronomic guidance, AI assistance, farmer-to-farmer connections, and creative environmental sonification. The design intentionally keeps agronomic evidence separate from inferences and simulated examples.

**Stack:** Python 3.10+ (recommended Python 3.11 or 3.12), FastAPI, SQLite, vanilla JavaScript, MapLibre GL JS. No frontend build tooling is required.

## Quick start (Windows / macOS / Linux)

1. Extract the ZIP and open a terminal in the **agromatch** folder.
2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   # Windows cmd:        .venv\Scripts\activate.bat
   # macOS/Linux:        source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```
3. Copy `.env.example` to `.env`. **Do not put real tokens in the frontend or commit `.env`.** AI and AppEEARS credentials are optional for testing the other features.
4. Run from the project folder:

   ```bash
   uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```
5. Open http://127.0.0.1:8000 in a web browser. Register, create a farm, and draw at least one field to unlock analytical functions.

The initial SQLite schema and **two additive migrations** run automatically at startup. No manual migration command is required. Generated `.wav` files are placed in `storage/audio/`; the default SQLite database is `agromatch.db` in the project folder. Existing databases are not intentionally overwritten. Back them up before upgrading.

### Docker (optional)

```bash
docker build -t agromatch .
docker run --rm -p 8000:8000 -v agromatch_storage:/app/storage \
  -e DATABASE_PATH=storage/agromatch.db --env-file .env agromatch
```

On Windows PowerShell, use a single line or PowerShell line continuations instead of `\`. Create your `.env` file before using `--env-file`; remove that switch if you don't need external credentials.

## Features

| Section | Functions |
|---|---|
| Dashboard | Farm/field overview, latest weather preview, community highlights, alerts, shortcuts |
| Earth & Satellite Map | Field polygons; globe and NASA GIBS image overlays; NASA POWER climate snapshots; AppEEARS request/status/point-data panel |
| My Fields | Register/edit field boundaries, area, soil description, crop history, detailed field charts and snapshots |
| AI Field Doctor | Rule-based climate/vegetation indicators; optional AI interpretation with explicit evidence labels |
| Weather & Climate | Seven-day Open-Meteo forecast, heat/frost/heavy-rain/dry-weather alerts, NASA POWER historical context |
| Rotation Remix | Current, balanced, drought-resilient and soil-building scenarios (peer rotation is an optional fifth); heuristic stress comparisons with farmer-priority notes |
| Farm Copilot | Context-aware agriculture Q&A with Gemini primary and Grok fallback |
| Farm Match | Farmer profiles, compatibility explanation, like/pass, mutual match notifications |
| Farm Chat | Messages between matched farms, history, unread counters, WebSocket updates |
| Farm Feed | Member posts, likes, comments, activity notifications |
| Farm Symphony | Original procedural music from selected field signals, play/pause and saved tracks |
| Knowledge Hub | Nine searchable, categorized guidance articles |
| Reports | Printable HTML reports (print to PDF in browser) and CSV export |
| Notifications | Central view and read/unread support |

The UI uses dark forest-green, olive and warm cream tones, desktop/tablet/mobile responsive navigation and distinct evidence tags. Photos/uploads are **not yet supported** in the feed.

## External data and API settings

Copy `.env.example` and configure as necessary.

- **NASA POWER:** accessed automatically for long-term gridded rainfall, temperature, and **modelled** root-zone wetness. When unreachable, the original fallback provides **clearly labelled SIMULATED** monthly data. These are not true field measurements.
- **NASA GIBS:** visual image layers, served from NASA tiles; map controls also depend on MapLibre CDN and external basemap/terrain endpoints. Visibility depends on available imagery and layer identifiers. Map tile availability has not been verified on every region/date.
- **NASA AppEEARS / Earthdata:** enter `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD` or a valid `APPEEARS_TOKEN` issued by the AppEEARS service. AppEEARS requests are **on demand** for field-centre points, not polygon averages. The default requested product is `MOD13Q1.061` / `_250m_16_days_NDVI`. Product/layer pairs can be configured with `APPEEARS_LAYERS_JSON` using identifiers verified against the current AppEEARS product catalog. Task checks are initiated using **Check status** in the satellite UI; there is no autonomous polling worker yet. Product-specific data units, QA flags, and native resolutions require scientific validation. SMAP and ECOSTRESS numeric extraction/visualisation are **not turnkey**; configure and verify corresponding layers first.
- **Open-Meteo:** forecast is retrieved on demand. The forecast, not an observation, is displayed with its own source label. If the service is unavailable, the weather screen shows an explicit error rather than fake weather.
- **Gemini / Grok:** set `AI_PRIMARY_API_KEY` and `AI_BACKUP_API_KEY` on the **server**. Gemini uses the `generateContent` API; Grok uses the xAI OpenAI-compatible endpoint. Copilot and AI Field Doctor require a valid account/network connection, but ordinary rule-based diagnostic features work without AI keys. No AI key is included in this package.

### What satellite readings can (and cannot) tell you

A high/low NDVI or unusual trend is a **potential indicator**, not a plant disease diagnosis. POWER and SMAP are spatially coarse, ECOSTRESS may have sparse observations, and MODIS NDVI is limited by resolution, clouds, retrieval flags, and sensor characteristics. Soil nutrient content and crop disease **cannot be conclusively established from these data alone**. Verify field recommendations with on-site inspection, laboratory testing and local agronomic expertise. Harmony/rotation/matching scores are **relative heuristics**; they do not forecast guaranteed yields or profits. Procedural audio is an artistic sonification, not a validated scientific instrument.

## Tests

From the project root:

```bash
python -m pytest -q backend/tests
node frontend/tests/smoke.js
node --check frontend/app.js
node --check frontend/features.js
python -m compileall -q backend
```

The included backend suite uses FastAPI TestClient, an isolated temporary SQLite database and **mocked NASA/Gemini/Grok/Open-Meteo services**; it checks auth, fields, diagnoses, feed, notifications, chat, exports, database migrations, AppEEARS task flow, AI fallback, sonification API, and rotation scenario coverage. The frontend smoke test renders 13 section templates in a Node VM without opening a real browser. These are **not a replacement** for full browser end-to-end tests or live third-party service checks.

See `IMPLEMENTATION.md` for file changes, verification results and limitations.

## Hosting and privacy

This is a **Python web application**, not a static HTML bundle. Netlify Drop and GitHub Pages cannot host its FastAPI/SQLite backend by uploading the frontend folder alone. For a public demo, deploy the Docker image on a service that runs Python containers and provides **persistent storage**. Set `DATABASE_PATH=storage/agromatch.db` and mount `/app/storage` on a durable volume. HTTPS is required for public use.

**Prototype/security limitations:** Local SQLite + per-process WebSocket tracking is intended for small demos, not high-traffic production. Before exposing real farmer data to the public, implement login rate limiting, secure account recovery and deletion, stronger session management, media validation if uploads are enabled, privacy notice/consent, spam moderation, logging, reliable task workers, database backups, and multi-instance message distribution. Demo farm identities and values are simulated. Avoid deploying demo and actual private field data without a review of privacy and authorization requirements.

## Project layout

- `backend/main.py` - FastAPI routes, persistence, backgroundless integrations and report output.
- `backend/agro_services.py` - climate forecast, heuristic diagnostic service.
- `backend/appeears.py` - Earthdata/AppEEARS client and point-CSV parser.
- `backend/ai.py` - Gemini and Grok AI providers.
- `backend/knowledge.py` - searchable agronomy articles.
- `backend/env.py`, `music.py`, `rotation.py` - original NASA POWER, music and rotation engines.
- `backend/schema.sql`, `backend/migrations/*.sql` - original schema and additive migrations.
- `frontend/index.html`, `app.js`, `features.js`, `design.css` - responsive UI.
- `backend/tests/`, `frontend/tests/` - automated tests.
- `.env.example`, `Dockerfile` - example configuration/deployment.
