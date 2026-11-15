"""Worldwide parcel geometry and missing-data weather regression tests."""
import asyncio
import math

import agro_services
import geo_utils


def test_almaty_parcel_and_boundary():
    parcel = [[76.920, 43.240], [76.921,43.240],
              [76.921,43.241], [76.920,43.241]]
    assert geo_utils.contains_point(76.9205,43.2405,parcel)
    assert geo_utils.contains_point(76.920,43.2405,parcel)
    assert not geo_utils.contains_point(76.925,43.2405,parcel)
    assert 0.5 < geo_utils.area_ha(parcel) < 1.5


def test_dateline_parcel_is_not_worldwide():
    parcel=[[179.9,10.0],[-179.9,10.0],[-179.9,10.1],[179.9,10.1]]
    assert geo_utils.contains_point(179.95,10.05,parcel)
    assert geo_utils.contains_point(-179.95,10.05,parcel)
    assert not geo_utils.contains_point(0,10.05,parcel)
    assert 15000 < geo_utils.area_ha(parcel) < 30000


def test_missing_precipitation_does_not_create_false_dry_alert():
    days=[{"date":"2026-11-16","low":2,"high":19,"rain":None},
          {"date":"2026-11-17","low":3,"high":20,"rain":2}]
    assert not any(x["kind"]=="Dry weather" for x in agro_services.weather_warnings(days))


def test_complete_dry_forecast_does_create_alert():
    days=[{"date":"2026-11-16","low":2,"high":19,"rain":1},
          {"date":"2026-11-17","low":3,"high":20,"rain":2}]
    assert any(x["kind"]=="Dry weather" for x in agro_services.weather_warnings(days))


def test_forecast_returns_missing_values_and_refresh_bypasses_cache(monkeypatch):
    calls=[]
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {
                "timezone":"Asia/Almaty",
                "daily":{"time":["2026-11-16","2026-11-17"],
                    "temperature_2m_max":[14,None],
                    "temperature_2m_min":[1,None],
                    "precipitation_sum":[None,2],
                    "precipitation_probability_max":[40,None],
                    "weather_code":[3,61],
                    "wind_speed_10m_max":[12]},
                "hourly":{"relative_humidity_2m":[62,63]}
            }
    class Client:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        async def get(self,url,params):
            calls.append(url)
            return Response()
    monkeypatch.setattr(agro_services.httpx,"AsyncClient",Client)
    agro_services._cache.clear()
    a=asyncio.run(agro_services.forecast(43.24,76.92))
    assert a["days"][0]["rain"] is None
    assert a["days"][1]["high"] is None
    assert a["complete_days"] == 0
    assert not any(x["kind"]=="Dry weather" for x in a["warnings"])
    asyncio.run(agro_services.forecast(43.24,76.92))
    assert len(calls)==1
    asyncio.run(agro_services.forecast(43.24,76.92,refresh=True))
    assert len(calls)==2
