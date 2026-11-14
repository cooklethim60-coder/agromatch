import datetime as dt
from unittest.mock import AsyncMock
import pytest
import nasa_intelligence as ni
import main, appeears


def test_daily_power_metrics_and_missing_values():
    data={'properties':{'parameter':{
        'T2M':{'20260101':10,'20260102':20,'20260103':-999},
        'T2M_MIN':{'20260101':-2,'20260102':5},
        'T2M_MAX':{'20260101':22,'20260102':38},
        'PRECTOTCORR':{'20260101':0,'20260102':22,'20260103':7},
        'ALLSKY_SFC_SW_DWN':{'20260101':3,'20260102':4}}}}
    r=ni.analyze_power(data,dt.date(2026,1,1),dt.date(2026,1,3))
    assert r['period']['valid_days']==2
    assert r['indicators']['rain_total_mm']==22
    assert r['indicators']['frost_days_min_le_0c']==1
    assert r['indicators']['heat_days_max_ge_35c']==1
    assert r['indicators']['heavy_rain_days_20mm']==1
    assert r['monthly'][0]['observed_days']==2

@pytest.mark.asyncio
async def test_missing_nasa_is_not_simulated(monkeypatch):
    ni._CACHE.clear()
    async def offline(*args,**kwargs):raise ValueError('no observations')
    monkeypatch.setattr(ni,'power_point',offline)
    r=await ni.field_intelligence(43.2,76.9,365,False,True)
    assert r['data']=={} and 'POWER' in r['unavailable']
    assert 'SIMULATED' not in str(r)


def test_authenticated_field_ownership_and_api(auth,monkeypatch):
    c,h,fid=auth['client'],auth['headers'],auth['fid']
    async def mock_data(*args,**kwargs):
        return {'data':{'POWER':{'period':{'valid_days':5}}},'unavailable':{},'catalog':{}}
    monkeypatch.setattr(main.nasa_intelligence,'field_intelligence',mock_data)
    r=c.get(f'/api/fields/{fid}/earth-intelligence',headers=h)
    assert r.status_code==200 and r.json()['data']['POWER']['period']['valid_days']==5
    assert c.get(f'/api/fields/{fid}/earth-intelligence').status_code==401
    assert c.get('/api/fields/999/earth-intelligence',headers=h).status_code==404
    assert c.get(f'/api/fields/{fid}/earth-intelligence?days=5000',headers=h).status_code==422


def test_satellite_catalog_rejects_unverified_layers(auth,monkeypatch):
    c,h,fid=auth['client'],auth['headers'],auth['fid']
    assert c.get(f'/api/fields/{fid}/satellite/catalog',headers=h).status_code==200
    assert c.post(f'/api/fields/{fid}/satellite/tasks',headers=h,json={'product':'bad','layer':'data'}).status_code==422
    assert c.post(f'/api/fields/{fid}/satellite/tasks',headers=h,json={'product':'SPL4SMGP.007'}).status_code==422
