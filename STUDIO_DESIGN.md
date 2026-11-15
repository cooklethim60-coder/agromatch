# AgroMatch Studio — interface upgrade

## Design direction
An original, map-first precision-agriculture workspace for Kazakhstan and international farmers. Research references for **interaction ideas only**, not code, screenshots, fonts or brand assets:
- OneSoil platform: https://onesoil.ai/ru/platform — concise field view, vegetation and weather workflow.
- EOSDA Crop Monitoring guide: https://eos.com/user-guide/crop-monitoring/fields/ — searchable fields, map tools, dated layers.
- xarvio FIELD MANAGER: https://www.xarvio.com/us/en/products/field-manager.html — action-oriented field monitoring.

No copied HTML/CSS/assets. Custom CSS is under `frontend/studio.css`, loaded after `design.css`.

## Implemented
- **New welcome and sign-in** — RU/EN language switch, responsive landing visuals and accessible form labels.
- **Command Center (Overview)** — NASA/Open-Meteo context, four computed farm KPIs, interactive parcel preview, model signal panel, field cards, weather and community blocks.
- **Earth Studio** — satellite map next to coordinate-specific inspection, saved-field shortcuts, dated GIBS imagery, 8-day date steps and opacity slider.
- **Fields** — search by field/crop/soil, sort by name/area, side-by-side field comparison, boundary GeoJSON export and quick actions.
- **Evidence transparency** — show SIMULATED as simulated; don't equate NASA POWER grid with a field sensor, don't equate GIBS visual tiles with pixel-accurate measurements.
- **Usability** — improved global header, keyboard focus states, mobile layouts, reduced-motion support, improved save-field failure recovery, and stale async-response protection when switching map fields.
- Existing AI Copilot, rotation planner, messages, NASA integrations and weather APIs remain present.

## What is **not** implemented
- Live numeric high-resolution NDVI/soil moisture on every click: GIBS imagery is a visual overlay. AppEEARS products still require verified product versions/QA.
- Full RU/EN/KZ translation: new views are bilingual, older features are only partly localized.
- Durable database storage on Render Free: SQLite is still ephemeral; real data need persistent PostgreSQL or equivalent.
- Formal agronomic validation, pixel-quality masking, parcel-level sensor measurements, full security audit or an offline-capable PWA.

## Suggested acceptance test
1. Check `https://agromatch-6gy4.onrender.com/health`, then sign in with a test account (not a real farm account).
2. Verify welcome, registration, RU/EN switch and responsive layout on a narrow phone.
3. Register a farm and field; return to Overview. Dashboard map must show the saved field contour.
4. Click field in map preview, open Field details, then use “Map” quick action to zoom Earth Studio to that same field.
5. Click inside polygon, review source-labelled Open-Meteo forecast and NASA POWER regional data; verify appropriate missing-data messaging on outages.
6. Change satellite layer, image date and opacity; no numeric values should be claimed from raster-tile colors.
7. Open Fields, filter by a crop, sort area, compare two fields and export `agromatch-my-fields.geojson`. Validate JSON as GeoJSON Polygon features.
8. Open Weather, AI Copilot, Rotation, Feed, Messages and Reports to confirm no regressions.
9. Test a failed field save: form should become usable again instead of leaving the button disabled.
10. Review CI in GitHub Actions. Browser and live NASA/Render connectivity still need real verification; passing source tests is not enough.

## Technical files
- `frontend/app.js`: welcome/auth, shared header, Command Center, Earth Studio, map and GeoJSON export.
- `frontend/features.js`: field filtering/sorting/comparison and asynchronous satellite-panel correctness.
- `frontend/studio.css`: visual system and responsive components.
- `frontend/index.html`: stylesheet and metadata.
- `frontend/tests/smoke.js`: UI rendering regressions.
