"""Weather and transparent agronomic rules. No fabricated measurements."""
import time
import httpx

_cache = {}

async def forecast(lat, lon):
    key = (round(lat, 2), round(lon, 2)); hit = _cache.get(key)
    if hit and time.time() - hit[0] < 900: return hit[1]
    params = {"latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 7,
              "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code",
              "hourly": "soil_moisture_9_to_27cm"}
    async with httpx.AsyncClient(timeout=16) as c:
        r = await c.get("https://api.open-meteo.com/v1/forecast", params=params)
        r.raise_for_status(); obj = r.json()
    d = obj.get('daily', {}); records = []
    for i, date in enumerate(d.get('time', [])):
        records.append({"date": date, "high": d['temperature_2m_max'][i], "low": d['temperature_2m_min'][i],
                        "rain": d['precipitation_sum'][i], "rain_chance": d['precipitation_probability_max'][i],
                        "code": d['weather_code'][i]})
    if not records: raise ValueError('Weather provider returned no forecast days')
    hourly = obj.get('hourly', {})
    wet = [v for v in hourly.get('soil_moisture_9_to_27cm', [])[:24] if isinstance(v, (int, float))]
    output = {"source": "Open-Meteo forecast model", "kind": "FORECAST", "fetched_at": time.time(),
              "timezone": obj.get('timezone'), "days": records,
              "modelled_soil_moisture": round(sum(wet)/len(wet), 3) if wet else None,
              "warnings": weather_warnings(records), "limitations": "Weather model, not a field sensor. Soil moisture is modelled and may be unavailable."}
    _cache[key] = (time.time(), output)
    return output

def weather_warnings(days):
    found = []
    for d in days:
        if d['low'] is not None and d['low'] <= 0: found.append({"date": d['date'], "level": "warning", "kind": "Frost", "text": "Forecast low at or below 0°C; check local frost risk."})
        if d['high'] is not None and d['high'] >= 35: found.append({"date": d['date'], "level": "warning", "kind": "Heat", "text": "Forecast high at least 35°C; assess crop heat stress."})
        if d['rain'] is not None and d['rain'] >= 20: found.append({"date": d['date'], "level": "warning", "kind": "Heavy rain", "text": "Forecast rain at least 20 mm/day; check runoff risk."})
    if sum(d['rain'] or 0 for d in days) < 5:
        found.append({"date": None, "level": "info", "kind": "Dry weather", "text": "Less than 5 mm forecast over seven days; check soil and water availability."})
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
