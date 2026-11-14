import asyncio
from unittest.mock import AsyncMock
import main, appeears, agro_services


def test_account_and_field(auth):
    c=auth['client'];h=auth['headers'];fid=auth['fid']
    me=c.get('/api/me',headers=h)
    assert me.status_code==200
    f=c.get(f'/api/fields/{fid}',headers=h).json()
    assert f['name']=='North Field' and f['area_ha']>0
    assert f['snapshots'][0]['metrics']['simulated'] is True
    assert c.get(f'/api/fields/{fid}').status_code==401
    assert c.get('/api/knowledge',headers=h).status_code==200
    doc=c.get(f'/api/fields/{fid}/doctor',headers=h).json()
    assert doc['method'].startswith('transparent')
    assert doc['data_is_simulated'] is True
    assert doc['findings']
    assert c.get('/api/knowledge/ndvi',headers=h).json()['title'].lower().find('ndvi')!=-1


def test_feed_notifications_and_chat(auth):
    c=auth['client'];h=auth['headers']
    post=c.post('/api/feed',headers=h,json={'body':'Wheat growth is on track'})
    assert post.status_code==200
    pid=post.json()['id']
    assert c.post(f'/api/feed/{pid}/like',headers=h).json()['likes']==1
    assert c.post(f'/api/feed/{pid}/comments',headers=h,json={'body':'Rainfall is low'}).status_code==200
    assert c.get('/api/feed',headers=h).json()[0]['comments'][0]['body']=='Rainfall is low'
    reg=c.post('/api/register',json={'email':'beta@example.org','password':'betapassphrase'})
    h2={'Authorization':'Bearer '+reg.json()['token']}
    c.post('/api/farm',headers=h2,json={'name':'Beta Farm','lat':42.0,'lon':75.0})
    assert c.post(f'/api/feed/{pid}/like',headers=h2).status_code==200
    notes=c.get('/api/notifications',headers=h).json()
    assert any(n['category']=='like' for n in notes)
    x=next(n for n in notes if n['category']=='like')
    assert c.post(f"/api/notifications/{x['id']}/read",headers=h).status_code==200
    assert any(n['is_read']==1 for n in c.get('/api/notifications',headers=h).json())
    a=c.get('/api/me',headers=h).json()['farm']['id'];b=c.get('/api/me',headers=h2).json()['farm']['id']
    assert not c.post('/api/swipe',headers=h,json={'to_farm':b,'like':True}).json()['match']
    r=c.post('/api/swipe',headers=h2,json={'to_farm':a,'like':True}).json();assert r['match']
    mid=r['match_id'];msg=c.post(f'/api/matches/{mid}/messages',headers=h,json={'body':'Hello partner'})
    assert msg.status_code==200
    assert c.get('/api/notifications',headers=h2).json()[0]['category']=='message'
    assert len(c.get(f'/api/matches/{mid}/messages',headers=h2).json())==1
    assert c.post('/api/swipe',headers=h,json={'to_farm':a,'like':True}).status_code==400


def test_weather_doctor_and_exports(auth,monkeypatch):
    c=auth['client'];h=auth['headers'];fid=auth['fid']
    async def fake_forecast(lat,lon):
        return {'source':'Open-Meteo forecast model','days':[{'date':'2026-11-14','high':37,'low':12,'rain':1,'rain_chance':10,'code':0}],
                'warnings':[{'date':'2026-11-14','level':'warning','kind':'Heat','text':'Hot day'}]}
    monkeypatch.setattr(main.agro_services,'forecast',fake_forecast)
    assert c.get(f'/api/fields/{fid}/weather',headers=h).json()['warnings'][0]['kind']=='Heat'
    html=c.get(f'/api/reports/fields/{fid}.html',headers=h)
    assert html.status_code==200 and 'Field report' in html.text and 'SIMULATED' in html.text
    csv=c.get(f'/api/reports/fields/{fid}.csv',headers=h)
    assert csv.status_code==200 and 'rain_mm' in csv.text and 'field' in csv.text
    assert c.get('/api/reports/fields/999.html',headers=h).status_code==404


def test_satellite_submission_refresh(auth,monkeypatch):
    c=auth['client'];h=auth['headers'];fid=auth['fid']
    async def fake_submit(*args):return ({'task_id':'task-123'},[{'product':'MOD13Q1.061','layer':'_250m_16_days_NDVI'}])
    async def fake_task(*args):return {'status':'done'}
    async def fake_bundle(*args):return {'files':[{'file_name':'MOD13Q1.061-results.csv','file_id':'f01'}]}
    async def fake_csv(*args):return 'Date,MOD13Q1_061_250m_16_days_NDVI\n2026-10-01,6700\n2026-10-17,5900\n'
    monkeypatch.setattr(main.appeears,'submit_point',fake_submit)
    monkeypatch.setattr(main.appeears,'get_task',fake_task)
    monkeypatch.setattr(main.appeears,'get_bundle',fake_bundle)
    monkeypatch.setattr(main.appeears,'get_csv',fake_csv)
    r=c.post(f'/api/fields/{fid}/satellite/tasks',headers=h)
    assert r.status_code==200,r.text
    tid=r.json()['id']
    assert c.post(f'/api/fields/{fid}/satellite/tasks',headers=h).status_code==409
    x=c.post(f'/api/fields/{fid}/satellite/tasks/{tid}/refresh',headers=h)
    assert x.status_code==200,x.text
    assert x.json()['status']=='done'
    obs=c.get(f'/api/fields/{fid}/satellite',headers=h).json()['observations']
    assert len(obs)==2 and obs[0]['value']==.59
    assert c.post(f'/api/fields/999/satellite/tasks/{tid}/refresh',headers=h).status_code==404


def test_ai_gemini_fallback(monkeypatch):
    async def bad(*args):raise ValueError('Gemini offline')
    async def good(*args):return 'A cautious agronomy explanation.'
    monkeypatch.setattr(main.ai,'providers',lambda: [{'tag':'primary','kind':'gemini','model':'gemini-test'}, {'tag':'backup','kind':'grok','model':'grok-test'}])
    monkeypatch.setattr(main.ai,'_gemini',bad);monkeypatch.setattr(main.ai,'_openai',good)
    text,provider=asyncio.run(main.ai.complete('context',[{'role':'user','content':'Hello'}]))
    assert 'cautious' in text and provider.startswith('backup:grok')


def test_migration_preserves_data(auth):
    c=auth['client'];h=auth['headers']; fid=auth['fid']
    main.init(); main.init()
    assert c.get(f'/api/fields/{fid}',headers=h).status_code==200
    assert len(main.q('SELECT * FROM schema_migrations'))==2


def test_ai_doctor_and_custom_symphony(auth,monkeypatch):
    c=auth['client'];h=auth['headers'];fid=auth['fid']
    async def fake_ai(system,msgs):return ('Evidence: simulated grid, check on site','test:gemini')
    monkeypatch.setattr(main.ai,'complete',fake_ai)
    r=c.post(f'/api/fields/{fid}/doctor/ai',headers=h)
    assert r.status_code==200,r.text
    assert 'simulated grid' in c.get(f'/api/fields/{fid}/doctor/ai/latest',headers=h).json()['content']
    assert 'Last AI Field Doctor' in c.get(f'/api/reports/fields/{fid}.html',headers=h).text
    def fake_render(*args):pass
    monkeypatch.setattr(main.music,'render',fake_render)
    r=c.post(f'/api/fields/{fid}/symphony',headers=h,json={'indicators':['rainfall','temperature']})
    assert r.status_code==200,r.text
    assert r.json()['info']['active_indicators']==['rainfall','temperature']
    assert c.post(f'/api/fields/{fid}/symphony',headers=h,json={'indicators':['unavailable']}).status_code==400
