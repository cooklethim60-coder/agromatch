"""Environmental data: NASA POWER fetch, metrics, Harmony score, similarity, music mapping text."""
import httpx, datetime as dt, math, statistics as st

POWER_SRC = "NASA POWER (daily, ~0.5°x0.625° grid; precipitation IMERG-corrected, soil wetness MERRA-2 modelled)"

async def fetch_power(lat, lon, days=760):
    end = dt.date.today() - dt.timedelta(days=4)
    start = end - dt.timedelta(days=days)
    q = {"parameters": "PRECTOTCORR,T2M,GWETROOT", "community": "AG", "longitude": round(lon, 4),
         "latitude": round(lat, 4), "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON"}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get("https://power.larc.nasa.gov/api/temporal/daily/point", params=q)
        r.raise_for_status()
    return r.json()["properties"]["parameter"], end

def monthly(p):
    acc = {}
    for d, v in p["PRECTOTCORR"].items():
        if v > -900: acc.setdefault(d[:6], {"r": [], "t": [], "w": []})["r"].append(v)
    for k, key in (("T2M", "t"), ("GWETROOT", "w")):
        for d, v in p[k].items():
            if v > -900: acc.setdefault(d[:6], {"r": [], "t": [], "w": []})[key].append(v)
    out = []
    for m in sorted(acc):
        a = acc[m]
        out.append({"m": f"{m[:4]}-{m[4:]}", "rain": round(sum(a["r"]), 1), "temp": round(st.mean(a["t"]), 1) if a["t"] else None,
                    "wet": round(st.mean(a["w"]), 3) if a["w"] else None, "days": len(a["r"])})
    return out

def window_metrics(months, end_off=0, simulated=False, last_obs=None):
    sub = months[len(months) - 12 - end_off: len(months) - end_off] if end_off else months[-12:]
    if len(sub) < 6: return None
    rain = [x["rain"] for x in sub]; temps = [x["temp"] for x in sub if x["temp"] is not None]; wet = [x["wet"] for x in sub if x["wet"] is not None]
    mr = st.mean(rain)
    return {"rain_mm": round(sum(rain) * 12 / len(rain)), "temp_c": round(st.mean(temps), 1), "wetness": round(st.mean(wet), 3),
            "rain_cv": round(st.pstdev(rain) / mr, 2) if mr else 1.5,
            "trend": round(st.mean(wet[-3:]) - st.mean(wet[:3]), 3), "ndvi": None, "monthly": sub, "months_covered": len(sub),
            "last_obs": last_obs, "simulated": simulated,
            "source": "SIMULATED demo data (NASA POWER unreachable)" if simulated else POWER_SRC,
            "limits": "Coarse grid cell (~50 km): indicative regional conditions, not field-scale measurement. NDVI numeric series not loaded (needs Earthdata credentials)."}

def simulated_months(lat, n=24):
    out = []; today = dt.date.today()
    for i in range(n, 0, -1):
        mo = (today.month - i - 1) % 12; y = today.year - ((i - today.month + 11) // 12)
        s = math.sin((mo - 2) / 12 * 2 * math.pi)
        out.append({"m": f"{y}-{mo+1:02d}", "rain": round(45 - 25 * s * (1 if lat > 0 else -1) + (i % 5) * 4, 1),
                    "temp": round(15 - 11 * math.cos(mo / 12 * 2 * math.pi) * (1 if lat > 0 else -1) * 0.8, 1),
                    "wet": round(0.45 - 0.13 * s + (i % 4) * 0.01, 3), "days": 30})
    return out

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

def harmony(m):
    comps = [("soil wetness", clamp(1 - abs(m["wetness"] - 0.55) / 0.55), .4), ("rainfall steadiness", clamp(1 - m["rain_cv"] / 1.2), .25),
             ("temperature stress", clamp(1 - max(0, (m["temp_c"] - 24) / 12, (6 - m["temp_c"]) / 12)), .2),
             ("moisture trend", clamp(.5 + m["trend"] * 2.5), .15)]
    if m.get("ndvi") is not None: comps.append(("vegetation (NDVI)", clamp(m["ndvi"] / .8), .3))
    tw = sum(c[2] for c in comps); score = round(100 * sum(c[1] * c[2] for c in comps) / tw)
    lvl = "EXCELLENT" if score >= 80 else "GOOD" if score >= 65 else "MODERATE" if score >= 50 else "POOR" if score >= 35 else "CRITICAL"
    return score, lvl, [{"name": n, "value": round(v, 2), "weight": round(w / tw, 2)} for n, v, w in comps]

def similarity(a, b):
    f = [("annual rainfall", a["rain_mm"] / 1200, b["rain_mm"] / 1200, 1.0, f'{a["rain_mm"]} vs {b["rain_mm"]} mm'),
         ("temperature", a["temp_c"] / 30, b["temp_c"] / 30, 1.0, f'{a["temp_c"]} vs {b["temp_c"]} °C'),
         ("soil wetness", a["wetness"], b["wetness"], 1.3, f'{a["wetness"]} vs {b["wetness"]}'),
         ("rain variability", a["rain_cv"] / 1.2, b["rain_cv"] / 1.2, .7, f'{a["rain_cv"]} vs {b["rain_cv"]}')]
    tw = sum(x[3] for x in f); d = math.sqrt(sum(x[3] * (x[1] - x[2]) ** 2 for x in f) / tw)
    return {"score": round(100 * math.exp(-3 * d)), "parts": [{"name": x[0], "closeness": round(100 * (1 - min(1, abs(x[1] - x[2]) * 2))), "detail": x[4]} for x in f],
            "note": "Environmental similarity only (weighted distance on 4 NASA-derived variables). It does NOT measure soil, crop or practice compatibility."}

def music_mapping(m, score, lvl):
    return [f"Harmony {score}/100 → mood '{lvl}': " + {"EXCELLENT": "major pentatonic, slow, consonant", "GOOD": "major scale, warm melody", "MODERATE": "modal scale, shifting rhythm, light tension", "POOR": "phrygian minor, sparse, dark", "CRITICAL": "locrian, dissonant intervals, low drone"}[lvl],
            f"Soil wetness {m['wetness']} → timbre (wetter = softer, drier = brighter/harsher).",
            f"Rain variability {m['rain_cv']} → rhythm fragmentation and tempo.",
            f"Temperature {m['temp_c']} °C → key/register (warmer = higher).",
            f"Moisture trend {m['trend']:+} → {'tension eases over time' if m['trend'] >= 0 else 'tension builds over time'}.",
            "Creative mapping, not a scientific measurement."]
