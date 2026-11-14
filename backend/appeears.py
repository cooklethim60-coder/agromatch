"""NASA AppEEARS point-task client. Never synthesize observations.

Earthdata credentials stay on the server. The product/layer list is intentionally
configurable because availability differs and must be checked against /product.
"""
import csv, io, os, json, datetime as dt
import httpx

BASE = 'https://appeears.earthdatacloud.nasa.gov/api'
DEFAULT_LAYERS = [{"product": "MOD13Q1.061", "layer": "_250m_16_days_NDVI"}]

class ConfigError(ValueError): pass

def configured_layers():
    try: layers=json.loads(os.getenv('APPEEARS_LAYERS_JSON','') or json.dumps(DEFAULT_LAYERS))
    except ValueError as e: raise ConfigError('APPEEARS_LAYERS_JSON must be valid JSON') from e
    if not isinstance(layers,list) or not layers or not all(isinstance(l,dict) and l.get('product') and l.get('layer') for l in layers):
        raise ConfigError('APPEEARS_LAYERS_JSON requires product/layer pairs')
    return layers

async def bearer():
    # AppEEARS tokens are different from ordinary Earthdata bearer tokens.
    explicit = os.getenv('APPEEARS_TOKEN','').strip()
    if explicit and not explicit.startswith('your-'): return explicit
    # EARTHDATA_TOKEN is an EDL token, NOT an AppEEARS task API token.
    # Do not send it to AppEEARS: the two tokens are not interchangeable.
    user = os.getenv('EARTHDATA_USERNAME','').strip(); password=os.getenv('EARTHDATA_PASSWORD','').strip()
    if not user or not password or password.startswith('your-'):
        raise ConfigError('Configure EARTHDATA_USERNAME/EARTHDATA_PASSWORD or APPEEARS_TOKEN on the server')
    async with httpx.AsyncClient(timeout=25) as c:
        r = await c.post(BASE+'/login', auth=(user,password))
        r.raise_for_status(); return r.json()['token']

async def request(method, path, *, token=None, payload=None):
    h={'Authorization': 'Bearer '+(token or await bearer())}
    async with httpx.AsyncClient(timeout=40) as c:
        r=await c.request(method,BASE+path,headers=h,json=payload)
        r.raise_for_status(); return r

# Candidate collections; availability and layer identifiers are checked live in AppEEARS.
CANDIDATES = {'MODIS NDVI': 'MOD13Q1.061', 'SMAP root-zone moisture': 'SPL4SMGP.007',
              'ECOSTRESS land surface temperature': 'ECO_L2T_LSTE.002'}

async def catalog(product=None):
    """Public AppEEARS product/layer metadata (no user credentials required)."""
    if product is not None and product not in CANDIDATES.values():
        raise ConfigError('Unsupported NASA product identifier')
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.get(BASE+'/product'+('/'+product if product else ''))
        r.raise_for_status()
        return r.json()

async def validate_layer(product, layer):
    if product not in CANDIDATES.values() or not isinstance(layer,str) or not layer or len(layer)>200:
        raise ConfigError('Product or layer not allowed')
    data=await catalog(product)
    if isinstance(data,dict) and layer in data:
        return True
    if isinstance(data,list) and any(isinstance(x,dict) and (x.get('Layer')==layer or x.get('layer')==layer) for x in data):
        return True
    raise ConfigError('Layer not listed in live NASA AppEEARS catalog')

async def submit_point(lat,lon,field_id,start,end,chosen_layers=None):
    layers = chosen_layers if chosen_layers is not None else configured_layers()
    payload={"task_type":"point", "task_name":f"AgroMatch-field-{field_id}-{dt.date.today().isoformat()}",
             "params":{"dates":[{"startDate":start.strftime('%m-%d-%Y'),"endDate":end.strftime('%m-%d-%Y')}],
                       "layers":layers,"coordinates":[{"id":str(field_id),"latitude":lat,"longitude":lon}]}}
    # Validate all configured layers against live NASA metadata before task submission.
    for entry in layers:
        await validate_layer(entry['product'], entry['layer'])
    r=await request('POST','/task',payload=payload)
    return r.json(), layers

async def get_task(task_id):
    return (await request('GET','/task/'+task_id)).json()

async def get_bundle(task_id):
    return (await request('GET','/bundle/'+task_id)).json()

async def get_csv(task_id,file_id):
    r=await request('GET',f'/bundle/{task_id}/{file_id}')
    if len(r.content)>4_000_000: raise ValueError('AppEEARS CSV exceeds 4 MB safety limit')
    return r.text

def parse_point_csv(data, product, field_id):
    """Extract dated numeric values from NASA AppEEARS point CSV formats.
    Unknown columns are skipped rather than guessed or assigned false units.
    """
    records=[]; reader=csv.DictReader(io.StringIO(data.lstrip('\ufeff')))
    if not reader.fieldnames: return []
    for line in reader:
        low={k.strip().lower(): v for k,v in line.items() if k is not None}
        date=next((low[k] for k in ('date','date_of_observation','observation_date','calendar_date') if low.get(k)),None)
        if not date: continue
        try: observed=dt.date.fromisoformat(date[:10]).isoformat()
        except ValueError: continue
        for key,val in line.items():
            if not key or not val: continue
            nm=key.lower()
            if not any(q in nm for q in ('ndvi','lst','soil_moisture','sm_rootzone','surface_temp')):continue
            if any(q in nm for q in ('quality','qa','error','flag','uncertainty')):continue
            try: value=float(val)
            except ValueError:continue
            if not (-1e10 < value < 1e10) or value in (-9999,-999,-32768):continue
            indicator='NDVI' if 'ndvi' in nm else 'surface_temperature' if 'lst' in nm or 'temp' in nm else 'soil_moisture'
            # MOD13Q1 raw values are often scaled integers; only apply known scale.
            if indicator=='NDVI' and product.startswith('MOD13') and abs(value)>1: value*=.0001
            if indicator=='NDVI' and not -1<=value<=1:continue
            records.append({"field_id":field_id,"product":product,"indicator":indicator,"observed_at":observed,
                           "value":round(value,5),"unit":"index" if indicator=='NDVI' else 'raw product units (verify metadata)',
                           "resolution":"product-dependent","quality":"QA not independently checked"})
    return records
