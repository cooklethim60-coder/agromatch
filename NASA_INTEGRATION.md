# AgroMatch: NASA Earth Intelligence integration

## Implemented in this release

- **NASA POWER (numeric, no login):** `/api/fields/{field_id}/earth-intelligence?days=365` fetches daily temperature, daily minimum and maximum temperature, precipitation and solar radiation using the NASA POWER API. It computes precipitation totals, dry/heavy-rain days, frosts, heat days and monthly rainfall/temperature. Dates, missing-value handling, source and spatial limitations are included. Cache lifetime is six hours; append `&refresh=true` to bypass cache. API requires an authenticated owner of the field.
- **NASA POWER baseline used in Rotation Remix:** existing POWER snapshots drive crop strategy comparisons. Users can explicitly request an update with `POST /api/fields/{id}/refresh-climate`; if NASA POWER cannot be reached, the *legacy snapshot workflow* can fall back to clearly labelled SIMULATED values. **Do not use simulated values as evidence.** The new Earth Intelligence endpoint never fabricates missing NASA values.
- **NASA MODIS NDVI:** existing NASA AppEEARS point extraction, with Earthdata credentials server-side.
- **NASA SMAP / ECOSTRESS:** authenticated AppEEARS point extraction requests can now be selected in the Satellite Earth panel. The backend checks the chosen product/layer against the live AppEEARS catalog before submitting a task. Collection availability, coverage, scale, QA and sample values need to be checked against the returned metadata. Parsed temperature and soil-moisture values use **raw product units**, not automatically converted scientific units, and are **not included** in numeric crop scoring without validation. Some products may not be accessible in AppEEARS with the listed candidate version: a 503 or missing layer is an honest failure, not a simulated response.
- **SRTM 90 m:** optional point elevation from a **third-party OpenTopoData mirror**. This is derived from NASA SRTM; it is not a direct NASA endpoint, and one elevation is not a slope/erosion score.
- **NASA GIBS:** existing visual satellite raster overlays, not a numeric field measurement.

## Not yet a validated live data integration

- **GPM IMERG**: visual NASA layer may be available, but numeric IMERG processing requires a validated product download/subsetting workflow. NASA POWER precipitation is *not* equivalent to direct GPM IMERG extraction.
- **GRACE / GRACE-FO**: no numerical regional water-storage extraction in this release. These coarse-scale observations are not field-level measurements.
- **ECOSTRESS QA/cloud filtering** and **SMAP product scaling/QA**: collection selection is supported, but scientific validation of raw units and quality is required before using them quantitatively in crop scoring.
- **Local soil lab testing, irrigation system data, growing seasons, economics, verified crop outcomes** remain user/expert inputs, not satellite-derived results.

## Setup

1. Use Python 3.11+ and install `pip install -r backend/requirements.txt`.
2. Run `uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000` from project root.
3. Open the web app, register a farm and draw a field. Open **Satellite Earth** and select a field.
4. NASA POWER numerical records appear in **NASA Earth Intelligence**. Request optional SRTM elevation. A field's rotation baseline can be explicitly refreshed.
5. For MODIS/SMAP/ECOSTRESS extraction, set `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` in a private `.env` file or `APPEEARS_TOKEN` issued by AppEEARS. Do not commit these credentials. Select the dataset, fetch available layers, submit an extraction, and refresh the task status. AppEEARS is asynchronous.
6. Verify product metadata, QA flags, product scale/offset and local conditions before drawing scientific conclusions.

## API examples

`GET /api/fields/1/earth-intelligence?days=365&elevation=true`

`GET /api/fields/1/satellite/catalog?product=ECO_L2T_LSTE.002`

`POST /api/fields/1/satellite/tasks` with `{"product":"ECO_L2T_LSTE.002","layer":"<verified layer from catalog>"}`

All field endpoints require `Authorization: Bearer <session-token>`.

## Verification in authoring environment

- Backend unit and API tests: 13 passed; frontend syntax checks: passed.
- Live outgoing network requests to NASA were blocked in this environment, so **no successful end-to-end live NASA extraction is claimed**.
- Documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/ ; https://appeears.earthdatacloud.nasa.gov/ ; https://nsidc.org/data/user-resources/help-center/how-extract-point-and-area-data-samples-using-appeears
