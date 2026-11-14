"""Safe NASA connectivity checks: never expose or log credentials."""
import os
import httpx

POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
APPEEARS = "https://appeears.earthdatacloud.nasa.gov/api/product"

def configuration():
    has_edl = bool(os.getenv("EARTHDATA_TOKEN", "").strip())
    has_user = bool(os.getenv("EARTHDATA_USERNAME", "").strip())
    has_pass = bool(os.getenv("EARTHDATA_PASSWORD", "").strip())
    has_appeears = bool(os.getenv("APPEEARS_TOKEN", "").strip())
    return {
        "earthdata_bearer_configured": has_edl,
        "appeears_auth_configured": has_appeears or (has_user and has_pass),
        "appeears_auth_method": "appeears_token" if has_appeears else "earthdata_login" if has_user and has_pass else "missing",
        "note": "Earthdata Bearer token cannot replace an AppEEARS API token; credentials are never returned.",
    }

async def connectivity():
    result = {"configuration": configuration(), "services": {}}
    async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
        for name, url in (("NASA_POWER", POWER), ("NASA_APPEEARS_catalog", APPEEARS)):
            try:
                response = await client.get(url)
                result["services"][name] = {
                    "reachable": response.status_code < 500,
                    "http_status": response.status_code,
                    "note": "HTTP reachability only; not proof of valid credentials or usable observations",
                }
            except httpx.HTTPError:
                result["services"][name] = {"reachable": False, "error": "Network request failed"}
    return result
