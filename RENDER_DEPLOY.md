# Deploy AgroMatch on Render

## Repository
Upload the **contents** of the `agromatch` folder to the root of your GitHub repository (not the ZIP itself).

## Render
1. Dashboard → New → Blueprint.
2. Connect the GitHub repository and select `render.yaml`.
3. Approve the paid Starter web service and 1 GB persistent disk, or adapt the Blueprint to your needs.
4. Add optional environment secrets in the Render service dashboard (never in GitHub):
   - `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`, `APPEEARS_TOKEN` as needed for AppEEARS.
   - `AI_PRIMARY_API_KEY` and/or `AI_BACKUP_API_KEY` for AI providers.
5. Deploy, open the service URL, and visit `/health` to check basic availability.

The database uses `/app/storage/agromatch.db`; a persistent disk is required for durable SQLite data. The app does not require a build-time Earthdata credential. NASA APIs must be reachable from the deployed service for live observations. A passing `/health` only proves the web server is running, not that NASA APIs are accessible.

### Manual Render Web Service
Runtime: Docker; Dockerfile path: `./Dockerfile`; health check path: `/health`; disk mount: `/app/storage`; environment `DATABASE_PATH=/app/storage/agromatch.db`.

### Security
Do not commit `.env`, credentials, `.db`, WAV artifacts or private user data. Rotate any credentials previously included in a ZIP. Render Free has no persistent disks, so it is not suitable for persistent SQLite without external database migration.

## NASA credentials (important)
The Earthdata Login bearer token you created is **not** an AppEEARS task token.
In Render > Environment, set `EARTHDATA_TOKEN` to a **newly rotated** EDL token if using EDL-authenticated downloads. Do not put any token in the ZIP, GitHub, `.env.example`, or chat.
For AppEEARS point tasks, configure `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` **directly in Render**, or provide an AppEEARS-issued `APPEEARS_TOKEN` (short-lived). The backend calls the AppEEARS `/login` endpoint when credentials are present.
After logging in to AgroMatch, GET `/api/nasa/diagnostics` with the session bearer token to inspect connectivity without revealing secrets. This only checks reachability, not the correctness of satellite measurements.
