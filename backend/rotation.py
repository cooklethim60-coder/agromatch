"""Explainable crop-rotation scenario comparison.

All crop parameters are generic approximate references, not locally calibrated
agronomic recommendations. Outputs are relative scenario indicators, not yield
or profit predictions.
"""
from env import clamp

# water mm/season, N-fixation kg/ha (approx), soil-cover 0-1,
# drought sensitivity 0-1, crop family
CROPS = {
    "wheat": (450, 0, .60, .50, "cereal"),
    "barley": (400, 0, .55, .40, "cereal"),
    "maize": (600, 0, .45, .80, "cereal"),
    "oat": (380, 0, .55, .40, "cereal"),
    "sorghum": (380, 0, .50, .25, "cereal"),
    "sunflower": (500, 0, .40, .45, "oilseed"),
    "rapeseed": (450, 0, .60, .55, "oilseed"),
    "chickpea": (350, 50, .40, .35, "legume"),
    "lentil": (330, 45, .35, .35, "legume"),
    "pea": (380, 55, .40, .50, "legume"),
    "soybean": (520, 70, .45, .65, "legume"),
    "vetch": (300, 80, .80, .30, "legume"),
    "fallow": (0, 0, .10, 0, "fallow"),
}

def evaluate(seq, rain_mm, temp_c, rain_pct=0, temp_add=0, drought=0.0):
    supply = rain_mm * (1 + rain_pct / 100) * .6 * (1 - .4 * drought)
    rows = []
    for crop in seq:
        water, nitrogen, cover, sensitivity, family = CROPS[crop]
        need = water * (1 + .04 * temp_add)
        stress = 0 if not need else clamp((need - supply) / need * (.6 + sensitivity))
        rows.append({"crop": crop, "water_mm": round(need), "stress": round(stress, 2),
                     "n_fix": nitrogen, "cover": cover, "family": family})
    count = len(rows)
    mean_stress = sum(r["stress"] for r in rows) / count
    return {
        "seq": seq, "rows": rows,
        "water_mm": round(sum(r["water_mm"] for r in rows) / count),
        "stress": round(mean_stress, 2),
        "cover": round(sum(r["cover"] for r in rows) / count, 2),
        "n_fix": round(sum(r["n_fix"] for r in rows) / count),
        "yield_risk": "low" if mean_stress < .15 else "moderate" if mean_stress < .35 else "high",
        "supply_mm": round(supply),
        "legumes": sum(r["family"] == "legume" for r in rows),
        "repeat_family": any(rows[i]["family"] == rows[i - 1]["family"] != "fallow" for i in range(1, count)),
    }

def ai_sequence(rain_mm, temp_c, soil):
    ratio = rain_mm * .6 / 480
    seq = (["barley", "chickpea", "wheat", "vetch"] if ratio < .8 else
           ["wheat", "pea", "barley", "sunflower"] if ratio < 1.1 else
           ["maize", "soybean", "wheat", "rapeseed"])
    if soil and "clay" in soil.lower() and "chickpea" in seq:
        seq[seq.index("chickpea")] = "lentil"
    return seq

def drought_sequence(rain_mm, soil):
    """Conservative low-water alternative; generic and not a local planting prescription."""
    seq = ["sorghum", "chickpea", "barley", "vetch"] if rain_mm < 500 else ["barley", "lentil", "sorghum", "pea"]
    if soil and "clay" in soil.lower():
        seq = ["barley", "lentil", "sorghum", "vetch"]
    return seq

def soil_building_sequence(rain_mm, soil):
    """Legume/cover-oriented alternative intended to explore soil-cover and N cycling."""
    seq = ["vetch", "wheat", "pea", "barley"] if rain_mm < 750 else ["vetch", "maize", "soybean", "wheat"]
    if soil and "sand" in soil.lower():
        seq = ["vetch", "barley", "chickpea", "oat"]
    return seq

def _priority_notes(priorities, result):
    notes = []
    normalized = {str(p).strip().lower() for p in (priorities or [])}
    if any("water" in p for p in normalized):
        notes.append("Water priority: compare average crop water demand and the relative water-stress index.")
    if any("soil" in p for p in normalized):
        notes.append("Soil-health priority: compare soil-cover proxy and approximate legume nitrogen fixation.")
    if any("resilien" in p for p in normalized):
        notes.append("Resilience priority: review water-stress risk, crop-family diversity and local climate fit.")
    if any("profit" in p or "market" in p for p in normalized):
        notes.append("Profit/market priority is recorded but not scored: local prices, contracts and costs are not available.")
    if any("input" in p for p in normalized):
        notes.append("Low-input priority is not directly scored: fertilizer, labour, machinery and irrigation costs are unknown.")
    return notes

def compare(current, peer, rain_mm, temp_c, soil, soil_source, crops_known,
            rain_pct, temp_add, drought, priorities=None):
    current_seq = [c for c in current if c in CROPS] or ["wheat", "fallow"]
    definitions = [
        ("current", "Current rotation", current_seq,
         "Built from the crop history entered by the farmer."),
        ("ai", "Balanced recommendation", ai_sequence(rain_mm, temp_c, soil),
         "Rule-based alternative selected using effective rainfall, generic crop water needs, crop-family diversity and limited soil-texture information."),
        ("drought", "Drought-resilient option", drought_sequence(rain_mm, soil),
         "Low-water exploratory sequence using generic drought-sensitivity references; local growing-season and market checks are essential."),
        ("soil", "Soil-building option", soil_building_sequence(rain_mm, soil),
         "Legume/cover-oriented exploratory sequence intended to increase living cover and nitrogen-cycling opportunities."),
    ]
    if peer:
        peer_seq = [c for c in peer if c in CROPS]
        if peer_seq:
            definitions.append(("peer", "Peer rotation", peer_seq,
                "Reported by a matched farm with similar environmental conditions. Its soil, practices and outcomes may differ."))
    out = []
    for key, name, seq, why in definitions:
        e = evaluate(seq, rain_mm, temp_c, rain_pct, temp_add, drought)
        e.update(key=key, name=name, why=why)
        e["pros"] = (
            ([f"Approximate nitrogen fixation: {e['n_fix']} kg/ha/year average"] if e["n_fix"] else []) +
            ([f"Higher average soil-cover proxy ({e['cover']})"] if e["cover"] >= .55 else []) +
            (["Lower average crop water demand than 400 mm/season"] if e["water_mm"] < 400 else [])
        )
        e["cons"] = (
            (["Same crop family in consecutive years may increase pest/disease pressure"] if e["repeat_family"] else []) +
            (["Elevated relative water-stress index in this scenario"] if e["stress"] >= .35 else []) +
            (["No legume in rotation"] if not e["legumes"] else [])
        )
        e["assumptions"] = [
            "Effective rainfall = 60% of annual NASA POWER rainfall (rough screening assumption)",
            "No irrigation is included",
            "Crop water and nitrogen values are generic approximate references, not local measurements",
            "Stress is a relative screening index, not a yield or profit prediction",
            "Sequence order does not encode locally validated sowing/harvest dates",
        ]
        e["missing"] = (
            ([] if soil_source == "farmer-tested" else ["No laboratory soil test (pH, nutrients, organic matter, salinity, drainage)"]) +
            ([] if crops_known else ["Crop history is incomplete"]) +
            ["Local sowing windows, varieties and frost dates", "Market prices, labour and machinery availability",
             "Irrigation availability and actual field soil moisture", "Local pest and disease pressure"]
        )
        e["priority_notes"] = _priority_notes(priorities, e)
        out.append(e)
    return out
