import os, sys, tempfile, pathlib
import pytest
from fastapi.testclient import TestClient
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
# Isolate all test cases from each other's persisted state and user's actual database.
os.environ['DATABASE_PATH'] = 'backend/tests/test-agromatch.db'
import main

@pytest.fixture(autouse=True)
def clean_db(monkeypatch,tmp_path):
    main.DB=tmp_path/'test.sqlite3'
    main.init()
    async def fake_power(lat,lon,days=760):
        raise OSError('Network unavailable in unit tests')
    monkeypatch.setattr(main.env,'fetch_power',fake_power)
    yield

@pytest.fixture
def client():
    return TestClient(main.app)

@pytest.fixture
def auth(client):
    r=client.post('/api/register',json={'email':'a@example.org','password':'longpassword','name':'Alpha'})
    assert r.status_code==200
    h={'Authorization':'Bearer '+r.json()['token']}
    assert client.post('/api/farm',headers=h,json={'name':'Alpha Farm','region':'Kazakhstan','lat':43.2,'lon':76.7}).status_code==200
    p=[[76.7,43.2],[76.71,43.2],[76.71,43.21],[76.7,43.21]]
    r=client.post('/api/fields',headers=h,json={'name':'North Field','polygon':p,'soil':'loam','soil_source':'farmer-provided','crops':['2024 wheat','2025 pea','2026 barley']})
    assert r.status_code==200,r.text
    return {'headers':h,'fid':r.json()['id'],'client':client}
