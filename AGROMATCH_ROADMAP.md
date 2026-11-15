# AgroMatch roadmap — Kazakhstan and global

Target audiences: farmers, agronomists, NASA Space Apps Challenge judges. Show whether each figure is measured, modeled, derived, or simulated.

## Implemented in the first v3 improvement sprint
- Dateline-aware field point selection and approximate spherical polygon area (not a legal survey).
- Authorization-controlled point conditions, modeled forecast and numerical NASA POWER history with source notes.
- Missing precipitation is never automatically set to 0 mm; forced refresh bypasses forecast cache.
- Improved weather completeness indicators, global coordinate search, field point JSON export.
- Initial RU/EN navigation support (full translation remains unfinished).
- Visible Render Free SQLite storage-loss warning; CI and regression tests for geometry and weather.

## Next milestones, in priority order

| Priority | Workstream | Definition of done |
|---|---|---|
| P0 | Durable database | Move user records and sessions from SQLite to external PostgreSQL. Accounts and fields survive redeploys and sleep/restart cycles. |
| P0 | Security | Add rate limits, expiring sessions, password reset, account deletion, input validation and private farm-sharing controls. |
| P0 | Live integration verification | Check deployed NASA POWER, Open-Meteo and AppEEARS against real Kazakhstan/global field coordinates, dates, units and QA. Outages never generate invented values. |
| P1 | Numeric satellite data | Verify AppEEARS MODIS NDVI and optional SMAP/ECOSTRESS products, native pixel size, units, QA masks and date range. |
| P1 | Field-level aggregation | Compute polygon statistics only when a product has suitable resolution and verified QA; distinguish nearest pixel vs field aggregate. |
| P1 | Crop modeling | Add climate-aware crop calendars and locally calibrated assumptions; show source and confidence for rotation scenarios. |
| P1 | Localization and accessibility | Finish RU/EN site text, optionally Kazakh, responsive charts, keyboard/mobile accessible controls. |
| P2 | Collaboration | Moderate posts and messages; obtain consent for sharing field locations; export usable reports. |
| P2 | Competition demo | Two reproducible examples (Kazakhstan and an international location) with source references and a short walkthrough video. |

## Scientific constraints

NASA POWER provides regional gridded climate estimates, not readings from an in-field sensor. Open-Meteo supplies weather-model forecasts. NASA GIBS is a visual image service, not numerical measurements when clicking pixels. AppEEARS can provide point extractions when supported datasets are configured and QA is processed; an Earthdata bearer token is not necessarily an AppEEARS task token. SRTM point elevation is not a slope estimate. NDVI cannot alone identify crop disease or guarantee yield. Never bundle credentials or paste them into source code. Rotate previously exposed tokens.

## Kazakhstan/global acceptance checklist

1. Register a test farm in Kazakhstan and add a polygon by coordinates.
2. Open Satellite Earth, select a point inside the field, check map marker, signed-in authorization, source and measurement scope.
3. Open Weather & Climate; switch 3/7-day views and force an actual refresh. Check units and missing values.
4. Observe what happens if external services are offline: unavailable must not be replaced with a fictitious measurement.
5. Export point JSON and inspect coordinates, dates, sources and uncertainty.
6. Repeat with a polygon in another country and one crossing the International Date Line.
7. Verify user ownership checks, automatic tests, and deployment logs.
8. Do not enter valuable personal field data until storage is persistent.

## Free Render warning

The current Blueprint uses Render Free with ephemeral SQLite storage. Deploy success does NOT imply persistence; accounts/fields can be lost when the instance restarts or redeploys. Migrate to external durable storage for real farmers.

## Verification

GitHub Actions CI performs Python unit tests, Python compilation, frontend smoke tests, and JavaScript syntax checks. A green CI run is not a substitute for real NASA credentials, deployment connectivity, field inspection or privacy/security audit.
