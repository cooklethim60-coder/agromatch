"""Weather and transparent agronomic rules. No fabricated measurements."""
import time
import httpx

_cache = {}

async def forecast(lat, lon, refresh=False):
    """Forecast for selected coordinates, with explicitly missing values."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Invalid weather coordinates")
    key = (round(lat, 3), round(lon, 3))
    hit = _cache.get(key)
    if not refresh and hit and time.time() - hit[0] < 900:
        return hit[1]
    params = {
        "latitude": lat, "longitude": lon,
        "timezone": "auto", "forecast_days": 7,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code,wind_speed_10m_max",
        "hourly": "soil_moisture_9_to_27cm,relative_humidity_2m",
    }
    async with httpx.AsyncClient(timeout=18) as client:
        response = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        response.raise_for_status()
        obj = response.json()
    daily = obj.get("daily") or {}
    dates = daily.get("time") or []

    def value(name, index):
        series = daily.get(name) or []
        if index >= len(series):
            return None
        v = series[index]
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    days = []
    for i, date in enumerate(dates):
        days.append({
            "date": date, "high": value("temperature_2m_max", i),
            "low": value("temperature_2m_min", i),
            "rain": value("precipitation_sum", i),
            "rain_chance": value("precipitation_probability_max", i),
            "code": value("weather_code", i),
        })
    if not days or not any(d["high"] is not None or d["low"] is not None for d in days):
        raise ValueError("Weather service returned no usable daily temperatures")
    hourly = obj.get("hourly") or {}
    def first_day_values(name):
        return [v for v in (hourly.get(name) or [])[:24]
                if isinstance(v, (int, float)) and not isinstance(v, bool)]
    wet = first_day_values("soil_moisture_9_to_27cm")
    humidity = first_day_values("relative_humidity_2m")
    wind = value("wind_speed_10m_max", 0)
    output = {
        "source": "Open-Meteo weather forecast",
        "kind": "FORECAST", "fetched_at": time.time(),
        "timezone": obj.get("timezone"),
        "coordinates": {"lat":lat, "lon":lon},
        "units": {"temperature":"°C", "rain":"mm", "wind":"km/h",
                  "humidity":"%", "soil_moisture":"m³/m³"},
        "days": days, "complete_days": sum(
            1 for d in days if all(d[x] is not None for x in ("high","low","rain","rain_chance"))),
        "humidity_today": round(sum(humidity) / len(humidity)) if humidity else None,
        "wind_today": round(wind,1) if wind is not None else None,
        "modelled_soil_moisture": round(sum(wet)/len(wet),3) if wet else None,
        "warnings": weather_warnings(days),
        "limitations": "Forecast is model output for a grid cell, not a field sensor; missing values are shown as unavailable.",
    }
    _cache[key] = (time.time(), output)
    # Bound in-process cache; do not grow without limit on global map clicks.
    if len(_cache) > 512:
        oldest = min(_cache, key=lambda k: _cache[k][0])
        _cache.pop(oldest, None)
    return output

def weather_warnings(days):
    found = []
    for d in days:
        if d.get("low") is not None and d["low"] <= 0:
            found.append({"date": d["date"], "level":"warning", "kind":"Frost",
                          "text":"Minimum forecast temperature ≤ 0°C; inspect local frost risk."})
        if d.get("high") is not None and d["high"] >= 35:
            found.append({"date": d["date"], "level":"warning", "kind":"Heat",
                          "text":"Maximum forecast temperature ≥ 35°C; consider heat stress."})
        if d.get("rain") is not None and d["rain"] >= 20:
            found.append({"date": d["date"], "level":"warning", "kind":"Heavy rain",
                          "text":"Forecast rainfall ≥ 20 mm/day; inspect runoff and drainage."})
    # Do not create a dry-weather alert from missing precipitation predictions.
    if days and all(d.get("rain") is not None for d in days) and sum(d["rain"] for d in days) < 5:
        found.append({"date": None, "level":"info", "kind":"Dry weather",
                      "text":"Less than 5 mm forecast for the period; verify soil and irrigation needs."})
    return found[:15]

def diagnose(field, observations=None, weather=None):
    """Rule-based flags only; not disease identification or a trained diagnostic AI."""
    observations = observations or []
    snaps = field.get('snapshots') or []
    if not snaps: return {"field": field['name'], "method": "rule-based", "findings": [], "limitations": "No observations available"}
    m = snaps[0]['metrics']; simulated = bool(m.get('simulated'))
    source = 'SIMULATED' if simulated else m.get('source', 'NASA POWER')
    findings = []
    def add(level, title, evidence, interpretation, action, origin):
        findings.append(dict(level=level, title=title, evidence=evidence, interpretation=interpretation,
                             action=action, source=origin, is_diagnosis=False))
    if m.get('wetness') is not None and m['wetness'] < .32:
        add('warning', 'Dry root-zone context', f"Modelled soil wetness {m['wetness']}",
            'Regional water limitation is possible, not confirmed at the field.',
            'Check soil moisture in several field locations before irrigation.', source)
    if m.get('trend') is not None and m['trend'] < -.04:
        add('warning', 'Moisture trend is negative', f"Wetness trend {m['trend']:+.3f}",
            'Regional modeled moisture has declined.', 'Compare with soil samples and irrigation records.', source)
    if m.get('rain_cv') is not None and m['rain_cv'] > 1.3:
        add('info', 'Variable rainfall', f"Monthly rainfall CV {m['rain_cv']}",
            'Rainfall is uneven between months.', 'Check seasonal water storage and crop timing.', source)
    ndvi = sorted([o for o in observations if o['indicator'].lower() == 'ndvi'], key=lambda a:a['observed_at'])
    if len(ndvi) >= 2:
        a,b=ndvi[-2:]; gap=b['value']-a['value']
        if gap < -.12:
            add('warning','NDVI has decreased',f"NDVI {a['value']:.3f} → {b['value']:.3f}, {a['observed_at']} to {b['observed_at']}",
                'Vegetation activity may have decreased; seasonality, harvest and clouds can also cause it.',
                'Compare dates, quality masks, phenology, and inspect representative spots.', 'NASA AppEEARS (point sample)')
    if weather:
        for w in weather.get('warnings',[])[:4]:
            add(w['level'],w['kind'],w['text'], 'Forecast, not an observed event.',
                'Check local weather and consider crop-specific mitigation.', 'Open-Meteo forecast')
    if not findings:
        add('info','No rule-based flags','No configured thresholds were crossed.',
            'This does not prove the field is healthy.', 'Continue routine field inspection.', source)
    return {"field": field['name'], "method": "transparent rule-based flags (not disease AI)",
            "findings": findings, "data_is_simulated": simulated,
            "limitations": "NASA POWER is coarse regional/modelled data. AppEEARS point pixels may blend small fields. Field disease and yield cannot be diagnosed from these signals alone."}
