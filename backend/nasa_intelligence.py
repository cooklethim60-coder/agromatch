"""Evidence-first NASA climate analysis and opt-in SRTM elevation lookup.

No substituted observations. Outages are returned as unavailable states.
The SRTM lookup is a *third-party mirror* of NASA SRTM, NOT a NASA API.
"""
import datetime as dt
import math
import statistics as stats
import time
import httpx

_CACHE = {}
POWER_URL = 'https://power.larc.nasa.gov/api/temporal/daily/point'
ELEVATION_URL = 'https://api.opentopodata.org/v1/srtm90m'

def _valid(v):
    return isinstance(v, (float, int)) and math.isfinite(v) and v > -900

def analyze_power(properties, start, end):
    p = properties['properties']['parameter']
    t = p.get('T2M', {}); lo = p.get('T2M_MIN', {}); hi = p.get('T2M_MAX', {})
    rain = p.get('PRECTOTCORR', {}); solar = p.get('ALLSKY_SFC_SW_DWN', {})
    dates = sorted(set(t) & set(rain))
    observations = []
    for day in dates:
        if not (_valid(t[day]) and _valid(rain[day])): continue
        observations.append({'date':f'{day[:4]}-{day[4:6]}-{day[6:]}',
          'temperature_c':round(t[day],2), 'rain_mm':round(rain[day],2),
          'min_temp_c':round(lo[day],2) if _valid(lo.get(day)) else None,
          'max_temp_c':round(hi[day],2) if _valid(hi.get(day)) else None,
          'solar_kwh_m2_day':round(solar[day],2) if _valid(solar.get(day)) else None})
    if not observations: raise ValueError('NASA POWER returned no usable daily observations')
    months = {}
    for row in observations:
        key=row['date'][:7]
        months.setdefault(key,[]).append(row)
    monthly=[{'month':key,'rain_mm':round(sum(x['rain_mm'] for x in rows),1),
        'mean_temp_c':round(stats.mean(x['temperature_c'] for x in rows),1),
        'observed_days':len(rows)} for key,rows in sorted(months.items())]
    rainvals=[r['rain_mm'] for r in observations]
    temps=[r['temperature_c'] for r in observations]
    lows=[r['min_temp_c'] for r in observations if r['min_temp_c'] is not None]
    highs=[r['max_temp_c'] for r in observations if r['max_temp_c'] is not None]
    return {'source':'NASA POWER','source_url':POWER_URL,'kind':'regional gridded climate estimate',
            'period':{'requested_start':start.isoformat(),'requested_end':end.isoformat(),
                      'first_observation':observations[0]['date'],'last_observation':observations[-1]['date'],
                      'valid_days':len(observations)},
            'indicators':{'rain_total_mm':round(sum(rainvals),1),'mean_temp_c':round(stats.mean(temps),2),
                          'dry_days_under_1mm':sum(r<1 for r in rainvals),
                          'heavy_rain_days_20mm':sum(r>=20 for r in rainvals),
                          'frost_days_min_le_0c':sum(x<=0 for x in lows) if lows else None,
                          'heat_days_max_ge_35c':sum(x>=35 for x in highs) if highs else None,
                          'mean_solar_kwh_m2_day':round(stats.mean([r['solar_kwh_m2_day'] for r in observations if r['solar_kwh_m2_day'] is not None]),2) if any(r['solar_kwh_m2_day'] is not None for r in observations) else None},
            'monthly':monthly,'daily':observations,
            'limitations':['POWER gridded products are not in-field sensors.',
              'Partial months and missing values affect counts and totals.',
              'No crop-specific growing season or local irrigation is inferred.']}

async def power_point(lat,lon,days=365):
    if not (-90<=lat<=90 and -180<=lon<=180):raise ValueError('Invalid coordinates')
    if not 30<=days<=730:raise ValueError('Days must be in [30,730]')
    # Near real time API publication varies: avoid asserting the requested end exists.
    end=dt.date.today()-dt.timedelta(days=7)
    start=end-dt.timedelta(days=days-1)
    params={'parameters':'T2M,T2M_MIN,T2M_MAX,PRECTOTCORR,ALLSKY_SFC_SW_DWN',
            'community':'AG','longitude':round(lon,4),'latitude':round(lat,4),
            'start':start.strftime('%Y%m%d'),'end':end.strftime('%Y%m%d'),
            'format':'JSON','time-standard':'UTC'}
    async with httpx.AsyncClient(timeout=45) as c:
        r=await c.get(POWER_URL,params=params)
        r.raise_for_status()
        data=r.json()
    return analyze_power(data,start,end)

async def srtm_point(lat,lon):
    """Third-party OpenTopoData hosting of NASA SRTM 90m, not NASA-hosted."""
    if not (-90<=lat<=90 and -180<=lon<=180):raise ValueError('Invalid coordinates')
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.get(ELEVATION_URL,params={'locations':f'{lat:.5f},{lon:.5f}'})
        r.raise_for_status();data=r.json()
    records=data.get('results') or []
    value=records[0].get('elevation') if records else None
    if not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('No SRTM elevation for the requested coordinate')
    return {'elevation_m':round(value,1),'source':'NASA SRTM 90m (via third-party OpenTopoData mirror)',
            'source_url':ELEVATION_URL,'kind':'terrain elevation (not field slope)',
            'resolution':'approximately 90 m','limitations':'Point elevation only. Erosion risk or slope requires terrain analysis over the field polygon.'}

async def field_intelligence(lat,lon,days=365,elevation=False,refresh=False):
    key=(round(lat,4),round(lon,4),days,bool(elevation))
    hit=_CACHE.get(key)
    if hit and not refresh and time.monotonic()-hit[0]<21600:return hit[1]
    output={'coordinates':{'lat':lat,'lon':lon},'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),
            'data':{},'unavailable':{},'catalog':{
                'POWER':'numeric regional climate data; enabled without credentials',
                'MODIS':'numeric NDVI via authenticated AppEEARS point tasks',
                'SMAP':'requires authenticated NASA data extraction and product/layer validation',
                'ECOSTRESS':'requires authenticated NASA data extraction and product/layer validation',
                'GPM':'GIBS visual layer; numeric IMERG downloads need a separate validated access workflow',
                'GRACE-FO':'regional water storage dataset; not a field-level observation',
                'SRTM':'optional point elevation from public third-party SRTM mirror'}}
    try:output['data']['POWER']=await power_point(lat,lon,days)
    except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
        output['unavailable']['POWER']=f'{type(exc).__name__}: NASA POWER retrieval failed; no replacement data generated'
    if elevation:
        try:output['data']['SRTM']=await srtm_point(lat,lon)
        except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
            output['unavailable']['SRTM']=f'{type(exc).__name__}: elevation not available'
    if output['data']:_CACHE[key]=(time.monotonic(),output)
    return output
