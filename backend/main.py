import os, json, time, hashlib, secrets, asyncio, random, datetime as dt, math
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env"); load_dotenv(ROOT / "backend" / ".env")
import sqlite3
from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, Field, field_validator
import env, music, ai, rotation, agro_services, appeears, knowledge, nasa_intelligence, nasa_access
import csv, io, html

DB = ROOT / os.getenv("DATABASE_PATH", "agromatch.db"); AUDIO = ROOT / "storage" / "audio"; AUDIO.mkdir(parents=True, exist_ok=True)
def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c
def q(sql, a=(), one=False):
    c = db(); r = c.execute(sql, a).fetchall(); c.close(); r = [dict(x) for x in r]; return (r[0] if r else None) if one else r
def x(sql, a=()):
    c = db(); cur = c.execute(sql, a); c.commit(); i = cur.lastrowid; c.close(); return i

DEMO = [  # SIMULATED demo farms (clearly labelled in the UI)
 ("Olivares Estate", "Toledo, Spain", 39.86, -4.02, "no-till", ["wheat", "chickpea", "sunflower"], 1, dict(rain_mm=420, temp_c=15.5, wetness=.41, rain_cv=1.0, trend=.02)),
 ("Vega Alta Farm", "Segovia, Spain", 40.95, -4.12, "conventional", ["barley", "vetch", "wheat", "rapeseed"], 0, dict(rain_mm=520, temp_c=12.8, wetness=.5, rain_cv=.8, trend=.04)),
 ("Cortijo Sol", "Cuenca, Spain", 40.07, -2.13, "organic", ["wheat", "lentil", "fallow"], 1, dict(rain_mm=390, temp_c=13.9, wetness=.36, rain_cv=1.1, trend=-.03)),
 ("Prairie Gold", "Iowa, USA", 42.03, -93.6, "no-till", ["maize", "soybean"], 0, dict(rain_mm=900, temp_c=9.8, wetness=.58, rain_cv=.7, trend=.01)),
 ("Sahel Millet Co-op", "Maradi, Niger", 13.5, 7.1, "conventional", ["sorghum", "fallow"], 0, dict(rain_mm=480, temp_c=29.5, wetness=.2, rain_cv=1.6, trend=-.08)),
 ("Loire Valley Fields", "Tours, France", 47.4, 0.7, "regenerative", ["wheat", "pea", "barley", "rapeseed"], 1, dict(rain_mm=680, temp_c=11.9, wetness=.55, rain_cv=.6, trend=.05))]

def init():
    c = db(); c.executescript((ROOT / "backend" / "schema.sql").read_text())
    if not c.execute("SELECT 1 FROM farms WHERE is_demo=1").fetchone():
        for n, reg, la, lo, pr, rot, lb, m in DEMO:
            m = {**m, "ndvi": None, "monthly": [], "simulated": True, "last_obs": None, "source": "SIMULATED demo farm profile", "limits": "Demo data"}
            c.execute("INSERT INTO farms(name,region,lat,lon,practice,is_demo,demo_metrics,rotation,likes_back) VALUES(?,?,?,?,?,1,?,?,?)", (n, reg, la, lo, pr, json.dumps(m), json.dumps(rot), lb))
    # Idempotent additive migrations, also applied to older existing databases.
    c.execute("CREATE TABLE IF NOT EXISTS schema_migrations(name TEXT PRIMARY KEY, applied REAL)")
    for migration in sorted((ROOT / "backend" / "migrations").glob("*.sql")):
        if not c.execute("SELECT 1 FROM schema_migrations WHERE name=?", (migration.name,)).fetchone():
            c.executescript(migration.read_text(encoding="utf-8"))
            c.execute("INSERT INTO schema_migrations(name,applied) VALUES(?,?)", (migration.name, time.time()))
    c.commit(); c.close()
init()
app = FastAPI(title="AgroMatch")

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


# ---------- auth ----------
def hp(pw, salt): return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 120000)
class Reg(BaseModel): email: str; password: str; name: str = ""
class Login(BaseModel): email: str; password: str
def session(uid):
    t = secrets.token_hex(24); x("INSERT INTO sessions VALUES(?,?)", (t, uid)); return t
@app.post("/api/register")
def register(b: Reg):
    if len(b.password) < 6: raise HTTPException(400, "Password must be at least 6 characters")
    if q("SELECT 1 FROM users WHERE email=?", (b.email.lower(),)): raise HTTPException(409, "Email already registered")
    s = os.urandom(16); uid = x("INSERT INTO users(email,name,salt,pw,created) VALUES(?,?,?,?,?)", (b.email.lower(), b.name, s, hp(b.password, s), time.time()))
    return {"token": session(uid)}
@app.post("/api/login")
def login(b: Login):
    u = q("SELECT * FROM users WHERE email=?", (b.email.lower(),), True)
    if not u or not secrets.compare_digest(hp(b.password, u["salt"]), u["pw"]): raise HTTPException(401, "Wrong email or password")
    return {"token": session(u["id"])}
def me(authorization: str = Header(None)):
    t = (authorization or "").replace("Bearer ", ""); r = q("SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=?", (t,), True)
    if not r: raise HTTPException(401, "Not signed in")
    r["farm"] = q("SELECT * FROM farms WHERE user_id=?", (r["id"],), True); return r
def need_farm(u):
    if not u["farm"]: raise HTTPException(400, "Register your farm first")
    return u["farm"]["id"]

@app.get("/api/nasa/diagnostics")
async def nasa_diagnostics(u=Depends(me)):
    """Authenticated connectivity check; never returns credentials."""
    return await nasa_access.connectivity()

# ---------- farms & fields ----------
class FarmIn(BaseModel):
    name: str = Field(min_length=1,max_length=150)
    region: str = Field(default='',max_length=200)
    lat: float = Field(ge=-90,le=90)
    lon: float = Field(ge=-180,le=180)
    practice: str = Field(default='conventional',max_length=50)
    priorities: list[str] = Field(default_factory=list,max_length=12)
@app.post("/api/farm")
def farm(b: FarmIn, u=Depends(me)):
    if u["farm"]: x("UPDATE farms SET name=?,region=?,lat=?,lon=?,practice=?,priorities=? WHERE id=?", (b.name, b.region, b.lat, b.lon, b.practice, json.dumps(b.priorities), u["farm"]["id"]))
    else: x("INSERT INTO farms(user_id,name,region,lat,lon,practice,priorities) VALUES(?,?,?,?,?,?,?)", (u["id"], b.name, b.region, b.lat, b.lon, b.practice, json.dumps(b.priorities)))
    return {"ok": True}
def area_ha(ring):
    la0 = sum(p[1] for p in ring) / len(ring); k = 111320 * math.cos(math.radians(la0))
    pts = [(p[0] * k, p[1] * 110540) for p in ring]
    return round(abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))) / 2 / 10000, 2)
class FieldIn(BaseModel):
    name: str = Field(min_length=1,max_length=150)
    polygon: list[list[float]] = Field(min_length=3,max_length=300)
    soil: str = Field(default='',max_length=120)
    soil_source: str = Field(default='unknown',max_length=40)
    crops: list[str] = Field(default_factory=list,max_length=30)

    @field_validator('polygon')
    @classmethod
    def valid_boundary(cls,ring):
        if any(len(p)!=2 or not (-180<=p[0]<=180 and -90<=p[1]<=90) or not all(math.isfinite(v) for v in p) for p in ring):
            raise ValueError('Each polygon point must be [longitude, latitude] in valid ranges')
        if len({tuple(p) for p in ring})<3:
            raise ValueError('Field boundary needs at least 3 distinct corners')
        return ring
async def build_snapshots(fid, lat, lon):
    x("DELETE FROM snapshots WHERE field_id=?", (fid,))
    try:
        p, end = await env.fetch_power(lat, lon); months = env.monthly(p); sim = False; last = end.isoformat()
    except Exception:
        months = env.simulated_months(lat, 24); sim = True; last = None
    for label, off in (("now", 0), ("6 months ago", 6), ("12 months ago", 12)):
        m = env.window_metrics(months, off, sim, last)
        if m:
            s, l, _ = env.harmony(m); x("INSERT INTO snapshots(field_id,label,taken,metrics,harmony,level) VALUES(?,?,?,?,?,?)", (fid, label, (dt.date.today() - dt.timedelta(days=30 * off)).isoformat(), json.dumps(m), s, l))
async def save_field(farm_id, b, fid=None):
    ring = b.polygon
    if len(ring) < 3: raise HTTPException(400, "Draw at least 3 boundary points")
    lon = sum(p[0] for p in ring) / len(ring); lat = sum(p[1] for p in ring) / len(ring)
    a = (b.name, json.dumps(ring), area_ha(ring), b.soil, b.soil_source, json.dumps(b.crops), lat, lon)
    if fid: x("UPDATE fields SET name=?,polygon=?,area_ha=?,soil=?,soil_source=?,crops=?,lat=?,lon=? WHERE id=?", a + (fid,))
    else: fid = x("INSERT INTO fields(name,polygon,area_ha,soil,soil_source,crops,lat,lon,farm_id) VALUES(?,?,?,?,?,?,?,?,?)", a + (farm_id,))
    await build_snapshots(fid, lat, lon); return fid
def fld(f):
    f["polygon"] = json.loads(f["polygon"]); f["crops"] = json.loads(f["crops"])
    s = q("SELECT * FROM snapshots WHERE field_id=? ORDER BY taken DESC", (f["id"],)); 
    for r in s: r["metrics"] = json.loads(r["metrics"]); r["comps"] = env.harmony(r["metrics"])[2]
    f["snapshots"] = s; return f
def own_field(u, fid):
    f = q("SELECT * FROM fields WHERE id=? AND farm_id=?", (fid, need_farm(u)), True)
    if not f: raise HTTPException(404, "Field not found")
    return f
@app.post("/api/fields")
async def add_field(b: FieldIn, u=Depends(me)): return {"id": await save_field(need_farm(u), b)}
@app.put("/api/fields/{fid}")
async def edit_field(fid: int, b: FieldIn, u=Depends(me)): own_field(u, fid); return {"id": await save_field(need_farm(u), b, fid)}
@app.get("/api/me")
def get_me(u=Depends(me)):
    f = u["farm"]; fields = [fld(r) for r in q("SELECT * FROM fields WHERE farm_id=?", (f["id"],))] if f else []
    return {"user": {"id": u["id"], "name": u["name"], "email": u["email"]}, "farm": f, "fields": fields}
@app.get("/api/fields/{fid}")
def get_field(fid: int, u=Depends(me)): return fld(own_field(u, fid))

# ---------- farm metrics / discover ----------
def farm_metrics(f):
    if f["is_demo"]: return json.loads(f["demo_metrics"])
    r = q("SELECT s.metrics FROM snapshots s JOIN fields fl ON fl.id=s.field_id WHERE fl.farm_id=? AND s.label='now' ORDER BY s.id LIMIT 1", (f["id"],), True)
    return json.loads(r["metrics"]) if r else None
def farm_rot(f):
    if f["is_demo"]: return json.loads(f["rotation"])
    fl = q("SELECT crops FROM fields WHERE farm_id=? LIMIT 1", (f["id"],), True)
    return [c.split(" ", 1)[-1] for c in json.loads(fl["crops"])] if fl else []
def farm_compatibility(f, mine, environmental):
    """Transparent, weighted peer recommendation: climate + crops + practices + interests.

    Scores are relative discovery heuristics, not scientific compatibility or profit estimates.
    """
    if not mine or not environmental:return environmental
    parts=list(environmental['parts'])
    weighted=[(environmental['score'],.65)]
    mine_crops={c.lower() for c in farm_rot(mine)};other_crops={c.lower() for c in farm_rot(f)}
    if mine_crops and other_crops:
        overlap=round(100*len(mine_crops & other_crops)/len(mine_crops | other_crops))
        weighted.append((overlap,.20));parts.append({'name':'crop experience','closeness':overlap,
               'detail':', '.join(sorted(mine_crops & other_crops)) or 'No reported crops overlap'})
    if f.get('practice') and mine.get('practice'):
        same=f['practice']==mine['practice'];weighted.append((100 if same else 35,.10))
        parts.append({'name':'farming practice','closeness':100 if same else 35,
                      'detail':f"{mine['practice']} vs {f['practice']}"})
    try:
        pa=set(json.loads(mine.get('priorities') or '[]'));pb=set(json.loads(f.get('priorities') or '[]'))
    except (TypeError,ValueError):pa,pb=set(),set()
    if pa and pb:
        overlap=round(100*len(pa & pb)/len(pa | pb));weighted.append((overlap,.15))
        parts.append({'name':'shared priorities','closeness':overlap,
                      'detail':', '.join(sorted(pa & pb)) or 'No shared priorities reported'})
    total=sum(v*w for v,w in weighted)/sum(w for _,w in weighted)
    return {'score':round(total),'parts':parts,
            'environmental_score':environmental['score'],
            'note':'Peer discovery heuristic: climate (65% baseline), reported crops, practices and interests where available. Not a yield, soil or business outcome prediction.'}

def card(f, mine):
    m = farm_metrics(f); mm = farm_metrics(mine) if mine else None; sc, lv, comps = env.harmony(m) if m else (None, None, [])
    basic=env.similarity(mm,m) if m and mm else None
    return {"id": f["id"], "name": f["name"], "region": f["region"], "lat": f["lat"], "lon": f["lon"], "practice": f["practice"], "demo": bool(f["is_demo"]), "metrics": m, "harmony": sc, "level": lv,
            "priorities": json.loads(f.get('priorities') or '[]'),
            "rotation": farm_rot(f), "similarity": farm_compatibility(f,mine,basic),
            "area_ha": 0 if f["is_demo"] else sum(r["area_ha"] for r in q("SELECT area_ha FROM fields WHERE farm_id=?", (f["id"],)))}
@app.get("/api/discover")
def discover(u=Depends(me)):
    fid = need_farm(u); seen = {r["to_farm"] for r in q("SELECT to_farm FROM swipes WHERE from_farm=?", (fid,))}
    cards = [card(f, u["farm"]) for f in q("SELECT * FROM farms WHERE id!=?", (fid,)) if f["id"] not in seen and (f["is_demo"] or farm_metrics(f))]
    cards.sort(key=lambda c: -(c["similarity"]["score"] if c["similarity"] else 0)); return cards
@app.get("/api/farms/{fid}")
def farm_profile(fid: int, u=Depends(me)):
    f = q("SELECT * FROM farms WHERE id=?", (fid,), True)
    if not f: raise HTTPException(404, "No such farm")
    return card(f, u["farm"])
def pair(a, b): return (min(a, b), max(a, b))
class Swipe(BaseModel): to_farm: int; like: bool
@app.post("/api/swipe")
async def swipe(b: Swipe, u=Depends(me)):
    me_ = need_farm(u)
    if b.to_farm == me_ or not q("SELECT id FROM farms WHERE id=?", (b.to_farm,), True):
        raise HTTPException(400, "Invalid target farm")
    x("INSERT OR REPLACE INTO swipes VALUES(?,?,?)", (me_, b.to_farm, int(b.like)))
    if not b.like: return {"match": False}
    o = q("SELECT * FROM farms WHERE id=?", (b.to_farm,), True)
    back = o["likes_back"] if o["is_demo"] else (q("SELECT liked FROM swipes WHERE from_farm=? AND to_farm=?", (b.to_farm, me_), True) or {"liked": 0})["liked"]
    if not back: return {"match": False}
    a, c = pair(me_, b.to_farm)
    if not q("SELECT 1 FROM matches WHERE farm_a=? AND farm_b=?", (a, c)): x("INSERT INTO matches(farm_a,farm_b,created) VALUES(?,?,?)", (a, c, time.time()))
    m = q("SELECT id FROM matches WHERE farm_a=? AND farm_b=?", (a, c), True)
    if not o["is_demo"]: create_notification(b.to_farm, "match", "You have a new Farm Match", f"match:{m['id']}")
    await push(b.to_farm, {"type": "match", "match_id": m["id"]})
    return {"match": True, "match_id": m["id"], "simulated": bool(o["is_demo"])}

# ---------- chat ----------
clients = {}
async def push(farm_id, data):
    for w in list(clients.get(farm_id, ())):
        try: await w.send_json(data)
        except Exception: clients[farm_id].discard(w)
@app.websocket("/ws")
async def ws(w: WebSocket, token: str = ""):
    r = q("SELECT f.id FROM farms f JOIN sessions s ON s.user_id=f.user_id WHERE s.token=?", (token,), True)
    if not r: await w.close(code=4401); return
    await w.accept(); clients.setdefault(r["id"], set()).add(w)
    try:
        while True: await w.receive_text()
    except WebSocketDisconnect: clients[r["id"]].discard(w)
def my_match(u, mid):
    fid = need_farm(u); m = q("SELECT * FROM matches WHERE id=? AND (farm_a=? OR farm_b=?)", (mid, fid, fid), True)
    if not m: raise HTTPException(404, "No such match")
    m["other"] = m["farm_b"] if m["farm_a"] == fid else m["farm_a"]; return m
@app.get("/api/matches")
def matches(u=Depends(me)):
    fid = need_farm(u); out = []
    for m in q("SELECT * FROM matches WHERE farm_a=? OR farm_b=?", (fid, fid)):
        o = q("SELECT * FROM farms WHERE id=?", (m["farm_b"] if m["farm_a"] == fid else m["farm_a"],), True)
        last = q("SELECT * FROM messages WHERE match_id=? ORDER BY id DESC LIMIT 1", (m["id"],), True)
        out.append({"match_id": m["id"], "farm": card(o, u["farm"]), "last": last, "unread": q("SELECT COUNT(*) n FROM messages WHERE match_id=? AND sender_farm!=? AND read=0", (m["id"], fid), True)["n"], "created": m["created"]})
    out.sort(key=lambda r: -((r["last"] or {}).get("created") or r["created"])); return out
@app.get("/api/matches/{mid}/messages")
def msgs(mid: int, u=Depends(me)):
    m = my_match(u, mid); fid = need_farm(u); x("UPDATE messages SET read=1 WHERE match_id=? AND sender_farm!=?", (mid, fid))
    r = q("SELECT * FROM messages WHERE match_id=? ORDER BY id", (mid,))
    for i in r: i["payload"] = json.loads(i["payload"]) if i["payload"] else None
    return r
class Msg(BaseModel): body: str = ""; kind: str = "text"; payload: dict | None = None
async def post_msg(mid, sender, body, kind="text", payload=None):
    m = q("SELECT * FROM matches WHERE id=?", (mid,), True); i = x("INSERT INTO messages(match_id,sender_farm,kind,body,payload,created) VALUES(?,?,?,?,?,?)", (mid, sender, kind, body, json.dumps(payload) if payload else None, time.time()))
    r = q("SELECT * FROM messages WHERE id=?", (i,), True); r["payload"] = payload
    for f in (m["farm_a"], m["farm_b"]):
        if f != sender: create_notification(f, "message", "New message from a matched farm", f"match:{mid}")
        await push(f, {"type": "message", "message": r})
    return r
async def demo_reply(mid, demo_farm):
    await asyncio.sleep(2.5)
    await post_msg(mid, demo_farm, "[Simulated demo farmer – automatic reply] Thanks for connecting! Real farmers reply in person; this demo profile can't discuss real experience.")
@app.post("/api/matches/{mid}/messages")
async def send(mid: int, b: Msg, u=Depends(me)):
    m = my_match(u, mid)
    if b.kind not in ("text", "farm", "rotation", "track"):
        raise HTTPException(400, "Unsupported message type")
    if len(b.body) > 3000: raise HTTPException(400, "Message too long")
    if b.kind == "text" and not b.body.strip(): raise HTTPException(400, "Empty message")
    r = await post_msg(mid, need_farm(u), b.body.strip(), b.kind, b.payload)
    if q("SELECT is_demo FROM farms WHERE id=?", (m["other"],), True)["is_demo"]: asyncio.create_task(demo_reply(mid, m["other"]))
    return r
def create_notification(farm_id, category, message, target=""):
    x("INSERT INTO notifications(farm_id,category,text,target,created) VALUES(?,?,?,?,?)",
      (farm_id,category,message,target,time.time()))

@app.get("/api/notifications")
def notifs(u=Depends(me)):
    return q("SELECT * FROM notifications WHERE farm_id=? ORDER BY created DESC LIMIT 100", (need_farm(u),))

@app.post("/api/notifications/{notification_id}/read")
def read_notification(notification_id: int, u=Depends(me)):
    x("UPDATE notifications SET is_read=1 WHERE id=? AND farm_id=?", (notification_id, need_farm(u)))
    return {"ok": True}

# ---------- music ----------
def voice_params(m, lvl, seed, shift=0): return dict(level=lvl, seed=seed, temp_c=m["temp_c"], rain_cv=m["rain_cv"], wetness=m["wetness"], trend=m["trend"], shift=shift)
def make_track(farm_id, m, snap_id=None, kind="farm", secs=120, title=None, voices=None):
    sc, lvl, _ = env.harmony(m); seed = int(hashlib.md5(f"{farm_id}{snap_id}{m['wetness']}{m['rain_mm']}".encode()).hexdigest()[:8], 16)
    t = title or random.Random(seed).choice(music.TITLES[lvl]); i = x("INSERT INTO tracks(farm_id,snapshot_id,kind,title,level,harmony,created) VALUES(?,?,?,?,?,?,?)", (farm_id, snap_id, kind, t, lvl, sc, time.time()))
    fn = f"{i}.wav"; music.render(voices or [voice_params(m, lvl, seed)], secs, str(AUDIO / fn))
    info = {"mapping": env.music_mapping(m, sc, lvl), "mode": "Procedural demo mode (numpy synthesis, MUSIC_PROVIDER=procedural)", "simulated_data": m.get("simulated", False), "seconds": secs}
    x("UPDATE tracks SET file=?,info=? WHERE id=?", (fn, json.dumps(info), i)); return track(i)
def track(i):
    t = q("SELECT * FROM tracks WHERE id=?", (i,), True); t["info"] = json.loads(t["info"]); t["url"] = f"/audio/{t['file']}"; return t
@app.get("/api/farms/{fid}/track")
def farm_track(fid: int, snapshot_id: int | None = None, u=Depends(me)):
    f = q("SELECT * FROM farms WHERE id=?", (fid,), True)
    if not f: raise HTTPException(404, "Farm not found")
    if snapshot_id:
        s = q("SELECT s.* FROM snapshots s JOIN fields fl ON s.field_id=fl.id WHERE s.id=? AND fl.farm_id=?", (snapshot_id, fid), True)
        if not s: raise HTTPException(404, "Snapshot not found")
        m = json.loads(s["metrics"])
    else: m = farm_metrics(f); snapshot_id = 0
    if not m: raise HTTPException(400, "Farm has no environmental data yet")
    t = q("SELECT id FROM tracks WHERE farm_id=? AND snapshot_id=? AND kind='farm' AND file IS NOT NULL", (fid, snapshot_id), True)
    return track(t["id"]) if t else make_track(fid, m, snapshot_id)
class Orch(BaseModel): farm_ids: list[int]; name: str = ""
@app.post("/api/orchestra")
def orchestra(b: Orch, u=Depends(me)):
    fs = [q("SELECT * FROM farms WHERE id=?", (i,), True) for i in b.farm_ids[:8]]
    fs = [f for f in fs if f]
    ms = [m for f in fs if (m := farm_metrics(f))]
    if len(ms) < 2: raise HTTPException(400, "Select at least 2 farms with environmental data")
    avg = {k: round(sum(m[k] for m in ms) / len(ms), 3) for k in ("rain_mm", "temp_c", "wetness", "rain_cv", "trend")}; avg.update(ndvi=None, simulated=any(m.get("simulated") for m in ms))
    sc, lvl, _ = env.harmony(avg); vs = [voice_params(m, env.harmony(m)[1], 100 + i, shift=[0, 7, -5, 4][i % 4]) for i, m in enumerate(ms)]
    return make_track(need_farm(u), avg, None, "orchestra", 150, b.name or "Orchestra: " + " · ".join(f["name"] for f in fs[:3]), vs)
@app.get("/api/tracks")
def tracks(u=Depends(me)):
    saved = {r["track_id"] for r in q("SELECT track_id FROM saved_tracks WHERE user_id=?", (u["id"],))}
    out = []
    for t in q("SELECT id FROM tracks WHERE file IS NOT NULL ORDER BY id DESC LIMIT 60"):
        t = track(t["id"]); t["saved"] = t["id"] in saved; t["farm_name"] = (q("SELECT name FROM farms WHERE id=?", (t["farm_id"],), True) or {}).get("name"); out.append(t)
    return out
@app.post("/api/tracks/{tid}/save")
def save_track(tid: int, u=Depends(me)):
    if q("SELECT 1 FROM saved_tracks WHERE user_id=? AND track_id=?", (u["id"], tid)): x("DELETE FROM saved_tracks WHERE user_id=? AND track_id=?", (u["id"], tid)); return {"saved": False}
    x("INSERT INTO saved_tracks VALUES(?,?)", (u["id"], tid)); return {"saved": True}

# ---------- rotation & climate remix ----------
def field_ctx(u, fid):
    f = fld(own_field(u, fid)); now = next((s for s in f["snapshots"] if s["label"] == "now"), None); return f, now
@app.get("/api/rotation")
def rot(field_id: int, peer_farm_id: int | None = None, rain: float = 0, temp: float = 0, drought: float = 0, u=Depends(me)):
    f, now = field_ctx(u, field_id); m = now["metrics"]; crops = [c.split(" ", 1)[-1].lower() for c in f["crops"]]
    peer = None
    if peer_farm_id:
        other = q("SELECT * FROM farms WHERE id=?", (peer_farm_id,), True)
        if not other: raise HTTPException(404, "Peer farm not found")
        peer = farm_rot(other)
    return {"field": f["name"], "baseline": {"rain_mm": m["rain_mm"], "temp_c": m["temp_c"], "source": m["source"], "simulated": m["simulated"]}, "scenario": {"rain_pct": rain, "temp_add": temp, "drought": drought, "note": "Scenario simulation, NOT a forecast."},
            "strategies": rotation.compare(crops, peer, m["rain_mm"], m["temp_c"], f["soil"], f["soil_source"], len(crops) >= 3, rain, temp, drought, json.loads(u["farm"].get("priorities") or "[]"))}

# ---------- copilot ----------
MODES = {"ask": "Answer the farmer's question.", "do": "Produce a prioritised seasonal action plan (next 8 weeks): numbered tasks, why, what data supports it.", "plant": "Suggest crops/rotation options for this field with reasoning, risks and what to verify.",
         "buy": "List inputs to buy (seed, fertiliser, irrigation, etc.) with quantities per hectare as ranges. Give NO prices unless the farmer supplied them; say prices must be checked with local suppliers.",
         "budget": "Draft a budget structure with line items and formulas the farmer can fill with local prices. Do not invent prices.", "calendar": "Produce a month-by-month calendar of activities for the next 12 months for this field."}
class Chat(BaseModel):
    mode: str = Field(default='ask',max_length=20)
    message: str = Field(default='',max_length=4000)
    field_id: int | None = None
    history: list[dict] = Field(default_factory=list,max_length=12)
@app.post("/api/copilot")
async def copilot(b: Chat, u=Depends(me)):
    farm_ = u["farm"]; ctx = {"farm": {k: farm_[k] for k in ("name", "region", "practice", "priorities")}}
    if b.field_id:
        f, now = field_ctx(u, b.field_id); sn = {s["label"]: {k: s["metrics"][k] for k in ("rain_mm", "temp_c", "wetness", "rain_cv", "trend")} | {"harmony": s["harmony"], "level": s["level"]} for s in f["snapshots"]}
        ctx["field"] = {"name": f["name"], "area_ha": f["area_ha"], "soil": f["soil"] or "unknown", "soil_source": f["soil_source"], "crop_history": f["crops"], "nasa_power_snapshots": sn,
                        "data_source": now["metrics"]["source"], "simulated_data": now["metrics"]["simulated"], "last_obs": now["metrics"]["last_obs"], "monthly_last12": now["metrics"]["monthly"], "ndvi": "not available"}
        ctx["rotation_models"] = [{k: s.get(k) for k in ("name", "seq", "water_mm", "stress", "yield_risk", "n_fix")} for s in rot(b.field_id, None, 0, 0, 0, u)["strategies"] if not s.get("empty")]
    system = ("You are AgroMatch Farm Copilot. Use ONLY the JSON context below plus general agronomy knowledge. Rules: never invent soil test results, prices, yields or citations; "
              "if data is missing or simulated, say so; state assumptions, risks and data limitations explicitly; NASA POWER values are coarse grid data, not field measurements; "
              "recommend verifying with a local agronomist. Explain your reasoning briefly. Task: " + MODES.get(b.mode, MODES["ask"]) + "\nCONTEXT: " + json.dumps(ctx))
    msgs = [dict(role=m['role'],content=m['content'][:4000]) for m in b.history[-8:]
            if m.get('role') in ('user','assistant') and isinstance(m.get('content'),str)]
    msgs.append({"role": "user", "content": b.message or MODES.get(b.mode, "Help me.")})
    try: text, used = await ai.complete(system, msgs)
    except Exception as e: raise HTTPException(503, str(e))
    return {"text": text, "provider": used}
@app.get("/api/status")
def status(): return {"ai_providers": [{"tag": p["tag"], "kind": p["kind"], "model": p["model"]} for p in ai.providers()], "music": "procedural demo mode", "nasa_power": "live (falls back to labelled simulated data if unreachable)"}

# ---------- community feed ----------
class PostIn(BaseModel): body: str
class CommentIn(BaseModel): body: str

def feed_post(post, viewing_farm):
    row=q("SELECT name, region FROM farms WHERE id=?",(post['author_farm'],),True) or {}
    post.update(author=row.get('name','Unknown farm'), region=row.get('region',''),
                likes=q('SELECT COUNT(*) n FROM post_likes WHERE post_id=?',(post['id'],),True)['n'],
                liked=bool(q('SELECT 1 FROM post_likes WHERE post_id=? AND farm_id=?',(post['id'],viewing_farm),True)),
                comments=q('SELECT c.id,c.body,c.created,c.author_farm,f.name author FROM comments c JOIN farms f ON f.id=c.author_farm WHERE c.post_id=? ORDER BY c.id LIMIT 100',(post['id'],)))
    return post

@app.get('/api/feed')
def feed(limit: int = 30, before: int | None = None, u=Depends(me)):
    sql='SELECT * FROM posts WHERE id<? ORDER BY id DESC LIMIT ?' if before else 'SELECT * FROM posts ORDER BY id DESC LIMIT ?'
    rows=q(sql,(before,min(max(limit,1),50)) if before else (min(max(limit,1),50),))
    return [feed_post(p,need_farm(u)) for p in rows]

@app.post('/api/feed')
def post_feed(b:PostIn,u=Depends(me)):
    body=b.body.strip()
    if not 1 <= len(body) <= 2000: raise HTTPException(400,'Post must have 1–2000 characters')
    fid=need_farm(u); pid=x('INSERT INTO posts(author_farm,body,created) VALUES(?,?,?)',(fid,body,time.time()))
    return feed_post(q('SELECT * FROM posts WHERE id=?',(pid,),True),fid)

@app.post('/api/feed/{pid}/like')
def like_post(pid:int,u=Depends(me)):
    fid=need_farm(u); p=q('SELECT * FROM posts WHERE id=?',(pid,),True)
    if not p: raise HTTPException(404,'Post not found')
    if q('SELECT 1 FROM post_likes WHERE post_id=? AND farm_id=?',(pid,fid),True):
        x('DELETE FROM post_likes WHERE post_id=? AND farm_id=?',(pid,fid))
    else:
        x('INSERT INTO post_likes(post_id,farm_id) VALUES(?,?)',(pid,fid))
        if p['author_farm']!=fid:create_notification(p['author_farm'],'like','Your post received a like',f'post:{pid}')
    return feed_post(p,fid)

@app.post('/api/feed/{pid}/comments')
def comment_post(pid:int,b:CommentIn,u=Depends(me)):
    fid=need_farm(u); p=q('SELECT * FROM posts WHERE id=?',(pid,),True)
    if not p: raise HTTPException(404,'Post not found')
    body=b.body.strip()
    if not 1<=len(body)<=1000:raise HTTPException(400,'Comment must have 1–1000 characters')
    x('INSERT INTO comments(post_id,author_farm,body,created) VALUES(?,?,?,?)',(pid,fid,body,time.time()))
    if p['author_farm']!=fid:create_notification(p['author_farm'],'comment','New comment on your post',f'post:{pid}')
    return feed_post(p,fid)

# ---------- weather and field doctor ----------
@app.get('/api/fields/{fid}/weather')
async def field_weather(fid:int,u=Depends(me)):
    field=own_field(u,fid)
    try: return await agro_services.forecast(field['lat'],field['lon'])
    except Exception as e:raise HTTPException(503,f'Weather forecast unavailable: {type(e).__name__}')

@app.get('/api/fields/{fid}/doctor')
def field_doctor(fid:int,u=Depends(me)):
    field=fld(own_field(u,fid))
    obs=q('SELECT * FROM satellite_observations WHERE field_id=? ORDER BY observed_at DESC LIMIT 40',(fid,))
    return agro_services.diagnose(field,obs)

@app.post('/api/fields/{fid}/doctor/ai')
async def doctor_ai(fid:int,u=Depends(me)):
    f=fld(own_field(u,fid)); observations=q('SELECT * FROM satellite_observations WHERE field_id=? ORDER BY observed_at DESC LIMIT 40',(fid,))
    flags=agro_services.diagnose(f,observations)
    prompt=("You are an agricultural analytical assistant. Interpret ONLY the evidence below. "
            "Separate 'Observed evidence', 'Interpretation' and 'Suggested inspections'. "
            "Do not infer diseases, chemical prescriptions or yield figures. "
            "Explicitly mark SIMULATED data as unusable for live decisions. Cite sources by name, not invented literature. "
            "Use concise, practical language. Evidence JSON:\n"+json.dumps({"field":f['name'],"soil":f['soil'],
                "crops":f['crops'],"rule_based_flags":flags,"observations":observations[:20]}))
    try: answer,provider=await ai.complete(prompt,[{'role':'user','content':'Summarise possible agronomic concerns and what to check on site.'}])
    except Exception as e:raise HTTPException(503,'AI interpretation unavailable: '+type(e).__name__)
    x('INSERT INTO ai_field_insights(field_id,provider,content,created) VALUES(?,?,?,?)',
      (fid,provider,answer[:10000],time.time()))
    return {'text':answer,'provider':provider,'type':'AI interpretation, not field measurement or disease diagnosis',
            'evidence_count':len(observations)}

@app.get('/api/fields/{fid}/doctor/ai/latest')
def doctor_ai_latest(fid:int,u=Depends(me)):
    own_field(u,fid)
    return q('SELECT provider,content,created FROM ai_field_insights WHERE field_id=? ORDER BY id DESC LIMIT 1',(fid,),True)

# ---------- searchable educational library ----------
@app.get('/api/knowledge')
def knowledge_list(q:str='',category:str='',u=Depends(me)):
    need_farm(u)
    return [{k:v for k,v in a.items() if k!='body'} for a in knowledge.search(q,category)]

@app.get('/api/knowledge/{article_id}')
def knowledge_article(article_id:str,u=Depends(me)):
    need_farm(u)
    a=next((a for a in knowledge.search() if a['id']==article_id),None)
    if not a:raise HTTPException(404,'Article not found')
    return a

# ---------- printable and CSV field reports ----------
def report_data(fid,u):
    f=fld(own_field(u,fid)); s=f['snapshots'][0] if f['snapshots'] else None
    obs=q('SELECT product,indicator,observed_at,value,unit,quality FROM satellite_observations WHERE field_id=? ORDER BY observed_at DESC LIMIT 50',(fid,))
    d=agro_services.diagnose(f,obs)
    return f,s,obs,d

@app.get('/api/reports/fields/{fid}.html')
def report_html(fid:int,u=Depends(me)):
    f,s,obs,d=report_data(fid,u)
    def h(v):return html.escape(str(v))
    parts=["<!doctype html><html><head><meta charset='utf-8'><title>AgroMatch field report</title>",
           "<style>body{font:15px/1.55 system-ui;max-width:850px;margin:38px auto;color:#172b20;padding:0 18px}h1,h2{color:#1d5137}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ccc;padding:8px;text-align:left}.note{background:#f5f1e5;padding:12px}@media print{button{display:none}}</style></head><body>",
           "<button onclick='window.print()'>Print / Save PDF</button><h1>AgroMatch · Field report</h1>",
           f"<p>Field: <b>{h(f['name'])}</b> · {h(f['area_ha'])} ha · {h(f['lat'])}, {h(f['lon'])}</p>",
           f"<p>Soil: {h(f['soil'] or 'not recorded')} ({h(f['soil_source'])}) · crops: {h(', '.join(f['crops']))}</p>"]
    if s:
        m=s['metrics'];parts.extend(["<h2>Environmental context</h2>",
        f"<p>Rainfall {h(m['rain_mm'])} mm / approx 12 months; temperature {h(m['temp_c'])} °C; modelled root wetness {h(m['wetness'])}; heuristic Harmony {h(s['harmony'])}/100.</p>",
        f"<p class='note'>Source: {h(m['source'])}; last observation {h(m['last_obs'])}; simulated: {h(m['simulated'])}. Regional/modelled, NOT measured on this field.</p>"])
    parts.append('<h2>Field Doctor · rule-based indicators</h2>')
    for item in d['findings']:parts.append(f"<p><b>{h(item['title'])}</b> ({h(item['source'])})<br>{h(item['evidence'])}<br>{h(item['action'])}</p>")
    if s:
        try:
            seq=[c.split(' ',1)[-1].lower() for c in f['crops']]
            strategies=rotation.compare(seq,None,s['metrics']['rain_mm'],s['metrics']['temp_c'],f['soil'],f['soil_source'],len(seq)>=3,0,0,0)
            parts.append('<h2>Rotation comparison (relative heuristics)</h2><table><tr><th>Strategy</th><th>Water need</th><th>Stress index</th></tr>')
            for z in strategies:
                if not z.get('empty'):
                    parts.append(f"<tr><td>{h(z['name'])}</td><td>{h(z['water_mm'])} mm</td><td>{h(round(100*z['stress']))} / 100</td></tr>")
            parts.append('</table><p class="note">Generic indicative crop estimates, not yield or profit forecasts.</p>')
        except (KeyError,TypeError,ValueError):pass
    ai_latest=q('SELECT * FROM ai_field_insights WHERE field_id=? ORDER BY id DESC LIMIT 1',(fid,),True)
    if ai_latest:
        parts.append(f"<h2>Last AI Field Doctor interpretation</h2><p>{h(ai_latest['content'])}</p><p class='note'>AI GENERATED · {h(ai_latest['provider'])}. Verify all recommendations.</p>")
    parts.append('<h2>AppEEARS observations</h2><table><tr><th>Date</th><th>Indicator</th><th>Value</th><th>Quality</th></tr>')
    for o in obs:parts.append(f"<tr><td>{h(o['observed_at'])}</td><td>{h(o['indicator'])}</td><td>{h(o['value'])} {h(o['unit'])}</td><td>{h(o['quality'])}</td></tr>")
    parts.append('</table><p class="note">Field inspections and agronomist verification are essential. The diagnostic flags and rotation scores are heuristics, not yield or disease predictions.</p></body></html>')
    return HTMLResponse(''.join(parts),headers={'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'"})

@app.get('/api/reports/fields/{fid}.csv')
def report_csv(fid:int,u=Depends(me)):
    f,s,obs,d=report_data(fid,u); b=io.StringIO(); writer=csv.writer(b)
    writer.writerow(['field','date','source','indicator','value','unit','quality'])
    if s:
        m=s['metrics']
        for metric,unit in [('rain_mm','mm'),('temp_c','C'),('wetness','relative'),('rain_cv','relative')]:
            writer.writerow([f['name'],m.get('last_obs'),m['source'],metric,m.get(metric),unit,'coarse regional/modelled; simulated='+str(m['simulated'])])
    for o in obs:writer.writerow([f['name'],o['observed_at'],o['product'],o['indicator'],o['value'],o['unit'],o['quality']])
    return Response(b.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="field-{fid}.csv"'})

class SymphonyIn(BaseModel):
    indicators: list[str] = Field(default_factory=lambda:['rainfall','temperature','moisture','seasonal_change'],max_length=5)

@app.post('/api/fields/{fid}/symphony')
def field_symphony(fid:int,b:SymphonyIn,u=Depends(me)):
    f,now=field_ctx(u,fid)
    if not now:raise HTTPException(400,'No environmental data for this field')
    allowed={'rainfall','temperature','moisture','seasonal_change'}
    chosen=set(b.indicators)
    if not chosen or not chosen<=allowed:raise HTTPException(400,'Choose 1–4 supported environmental indicators')
    m=now['metrics'].copy()
    # Neutral creative sound parameters are not represented as measured values.
    neutral={'rainfall':('rain_cv',.75),'temperature':('temp_c',18.0),
             'moisture':('wetness',.5),'seasonal_change':('trend',0.0)}
    for indicator,(key,value) in neutral.items():
        if indicator not in chosen:m[key]=value
    t=make_track(need_farm(u),m,now['id'],'field',45,'Field Symphony · '+f['name'])
    info=t['info']; info['active_indicators']=sorted(chosen)
    info['mode']='Procedural creative sonification of selected environmental variables (unselected channels use neutral sound settings)'
    info['mapping']=[f"Active indicators: {', '.join(sorted(chosen))}",
                     "Unselected channels use neutral musical settings, NOT additional environmental measurements."] + env.music_mapping(now['metrics'],now['harmony'],now['level'])
    x('UPDATE tracks SET info=? WHERE id=?',(json.dumps(info),t['id']))
    return track(t['id'])

# ---------- NASA Earth Intelligence: live numerical evidence ----------
@app.get('/api/fields/{fid}/earth-intelligence')
async def earth_intelligence(fid: int, days: int = 365, elevation: bool = False,
                             refresh: bool = False, u=Depends(me)):
    f=own_field(u,fid)
    if not 30 <= days <= 730: raise HTTPException(422, 'days must be between 30 and 730')
    result=await nasa_intelligence.field_intelligence(f['lat'],f['lon'],days,elevation,refresh)
    result['field_id']=fid
    result['observations']=q('SELECT product,indicator,observed_at,value,unit,resolution,quality '
        'FROM satellite_observations WHERE field_id=? ORDER BY observed_at DESC LIMIT 100',(fid,))
    result['observation_note']='AppEEARS point observations; QA/units must be independently validated. They are not automatically converted into field-average soil measurements.'
    return result

@app.post('/api/fields/{fid}/refresh-climate')
async def refresh_field_climate(fid: int, u=Depends(me)):
    f=own_field(u,fid)
    # The existing snapshot ingestion remains separate from Earth Intelligence daily series.
    # Replacing a field snapshot can change rotation results and is explicit user action.
    await build_snapshots(fid,f['lat'],f['lon'])
    field=fld(own_field(u,fid))
    latest=next((v for v in field['snapshots'] if v['label']=='now'),None)
    return {'field_id':fid,'snapshot':latest,'warning':'SIMULATED snapshots are labelled if NASA POWER is unavailable; verify simulated flag before making decisions.'}

# ---------- AppEEARS on-demand task lifecycle ----------
def satellite_data(fid):
    return {"observations":q('SELECT * FROM satellite_observations WHERE field_id=? ORDER BY observed_at DESC LIMIT 200',(fid,)),
            "tasks":q('SELECT id,remote_id,status,products,created,checked,error FROM appeears_tasks WHERE field_id=? ORDER BY id DESC LIMIT 10',(fid,)),
            "limitations":"AppEEARS point sample, not a complete field polygon average. Quality and scale must be validated before agronomic use."}

@app.get('/api/fields/{fid}/satellite')
def sat_list(fid:int,u=Depends(me)):
    own_field(u,fid)
    return satellite_data(fid)

@app.get('/api/fields/{fid}/satellite/catalog')
async def satellite_catalog(fid:int, product:str|None=None, u=Depends(me)):
    own_field(u,fid)
    if product is None: return {'candidates':appeears.CANDIDATES,
        'note':'Product names are candidates, not a guarantee of temporal or spatial coverage. Check live layers for a supported product.'}
    if product not in appeears.CANDIDATES.values():raise HTTPException(422,'Unsupported product')
    try:return {'product':product,'layers':await appeears.catalog(product)}
    except Exception as exc:raise HTTPException(503,f'NASA catalog unavailable: {type(exc).__name__}')

class SatelliteLayerRequest(BaseModel):
    product: str | None = None
    layer: str | None = None

@app.post('/api/fields/{fid}/satellite/tasks')
async def sat_submit(fid:int, b:SatelliteLayerRequest | None=None, u=Depends(me)):
    f=own_field(u,fid);end=dt.date.today()-dt.timedelta(days=14);start=end-dt.timedelta(days=120)
    if q('SELECT 1 FROM appeears_tasks WHERE field_id=? AND status IN ("pending","processing","submitted")',(fid,)):
        raise HTTPException(409,'A satellite extraction task for this field is already running')
    if b and (b.product or b.layer):
        if not b.product or not b.layer:raise HTTPException(422,'Both NASA product and layer are required')
        try:await appeears.validate_layer(b.product,b.layer)
        except appeears.ConfigError as exc:raise HTTPException(422,str(exc))
        except Exception as exc:raise HTTPException(503,f'NASA layer validation failed: {type(exc).__name__}')
        selected=[{'product':b.product,'layer':b.layer}]
    else:selected=None
    try:
        if selected is None:result,layers=await appeears.submit_point(f['lat'],f['lon'],fid,start,end)
        else:result,layers=await appeears.submit_point(f['lat'],f['lon'],fid,start,end,selected)
    except appeears.ConfigError as e:raise HTTPException(503,str(e))
    except Exception as e:raise HTTPException(502,f'AppEEARS submission failed: {type(e).__name__}')
    remote=result.get('task_id')
    if not remote:raise HTTPException(502,'NASA response did not include task_id')
    i=x('INSERT INTO appeears_tasks(field_id,remote_id,status,products,created) VALUES(?,?,?,?,?)',
        (fid,remote,'submitted',json.dumps(layers),time.time()))
    create_notification(need_farm(u),'satellite','NASA extraction submitted',f'field:{fid}')
    return {'id':i,'remote_id':remote,'status':'submitted'}

@app.post('/api/fields/{fid}/satellite/tasks/{task_id}/refresh')
async def sat_refresh(fid:int,task_id:int,u=Depends(me)):
    own_field(u,fid); task=q('SELECT * FROM appeears_tasks WHERE id=? AND field_id=?',(task_id,fid),True)
    if not task:raise HTTPException(404,'Task not found')
    if task['status']=='done':return {'task':task,'data':satellite_data(fid)}
    try:
        status=await appeears.get_task(task['remote_id']); new_status=status.get('status','unknown')
        if new_status in ('done','complete','completed'):
            bundle=await appeears.get_bundle(task['remote_id'])
            counts=0
            for obj in bundle.get('files',[]):
                fn=obj.get('file_name','')
                if not fn.lower().endswith('.csv') or 'result' not in fn.lower():continue
                raw=await appeears.get_csv(task['remote_id'],obj['file_id'])
                # Point result files include the product identifier in their names.
                product=next((layer['product'] for layer in json.loads(task['products']) if layer.get('product') in fn), fn.split('-results')[0] or 'AppEEARS')
                for obs in appeears.parse_point_csv(raw,product,fid):
                    x('INSERT OR REPLACE INTO satellite_observations(field_id,source,product,indicator,observed_at,value,unit,resolution,quality,task_id) VALUES(?,?,?,?,?,?,?,?,?,?)',
                      (fid,'NASA AppEEARS',obs['product'],obs['indicator'],obs['observed_at'],obs['value'],obs['unit'],obs['resolution'],obs['quality'],task_id)); counts+=1
            new_status='done';msg=f'NASA task completed: {counts} dated values extracted. Review QA and raw product units.'
            create_notification(need_farm(u),'satellite',msg,f'field:{fid}')
        if new_status in ('error','failed'):
            create_notification(need_farm(u),'satellite','NASA extraction failed',f'field:{fid}')
        x('UPDATE appeears_tasks SET status=?,checked=?,error=NULL WHERE id=?',(new_status,time.time(),task_id))
    except Exception as e:
        x('UPDATE appeears_tasks SET checked=?,error=? WHERE id=?',(time.time(),type(e).__name__,task_id))
        raise HTTPException(502,f'AppEEARS status/download unavailable: {type(e).__name__}')
    return {'status':new_status,'data':satellite_data(fid)}

app.mount("/audio", StaticFiles(directory=AUDIO), name="audio")
@app.get("/")
def index(): return FileResponse(ROOT / "frontend" / "index.html")
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
