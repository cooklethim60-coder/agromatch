"""Editorial starter library: no invented citations or AI attribution."""
ARTICLES = [
 ('rotation','Crop rotation fundamentals','Crop rotation','Alternate crop families when possible. Cereals followed by legumes may diversify rooting and nutrient demand. Choose a sequence based on local disease pressure, water availability and markets.'),
 ('soil','What makes healthy soil?','Soil health','Healthy soil retains water, supports roots and soil organisms, and resists erosion. Check organic matter, compaction, pH and nutrient status with field samples. A satellite cannot measure nutrients directly.'),
 ('moisture','Understanding soil moisture','Soil & water','Moisture can be measured on site or estimated by models and satellites. NASA SMAP has a relatively coarse footprint. Always compare remote products with local measurements before scheduling irrigation.'),
 ('ndvi','How to interpret NDVI','Satellite intelligence','NDVI uses red and near-infrared reflectance to estimate vegetation greenness. A fall can reflect harvest, drought, cloud contamination, bare soil or disease; NDVI alone cannot distinguish the cause.'),
 ('satellite','NASA data: POWER, MODIS, SMAP and ECOSTRESS','Satellite intelligence','POWER gives gridded climate summaries. MODIS tracks large-area vegetation. SMAP estimates moisture on broad scales. ECOSTRESS observes surface temperature during available overpasses. Resolution, latency and quality matter.'),
 ('drought','Practical drought preparedness','Climate resilience','Track rainfall deficits and soil moisture, protect ground cover, adjust planting dates and evaluate drought-tolerant varieties using local trials. Verify water supply and irrigation efficiency.'),
 ('climate','Reading a 7-day agricultural forecast','Climate resilience','Forecasts describe possible future conditions and can change. Watch frost lows, high daytime heat and heavy rainfall, and compare forecast probabilities with field observations.'),
 ('sustainability','Farming while protecting the soil','Sustainable agriculture','Maintain cover where practical, reduce avoidable erosion, monitor nutrients, optimize water application and keep long-term crop records. Sustainable management depends on local soil and climate.'),
 ('legumes','Legumes and nitrogen fixation','Crop rotation','Rhizobia can fix atmospheric nitrogen in legume roots, but actual nitrogen credits depend on species, inoculation, soil and conditions. Do not treat indicative figures as fertilizer prescriptions.'),
]

def search(q='', category=''):
    items = [{"id": a, "title": b, "category": c, "body": d, "reading_minutes": 2, "type": "educational guide"} for a,b,c,d in ARTICLES]
    if category: items = [a for a in items if a['category'].lower() == category.lower()]
    if q: items = [a for a in items if q.lower() in (a['title']+' '+a['body']).lower()]
    return items
