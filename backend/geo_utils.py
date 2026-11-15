"""Small-field geometry helpers supporting polygons across the ±180° meridian.

Approximate spherical area; use geodetic GIS tools for surveyed boundaries.
Coordinates are (longitude, latitude). This module does not geocode addresses.
"""
import math

EARTH_RADIUS_M = 6371008.8

def _delta_lon(lon, reference):
    return (lon - reference + 180.0) % 360.0 - 180.0

def contains_point(lon, lat, ring):
    """Treat boundary points as inside. Unwrap around query longitude."""
    if len(ring) < 3 or not all(math.isfinite(x) for x in (lon, lat)):
        return False
    points = [(_delta_lon(x, lon), y) for x, y in ring]
    inside = False
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        cross = (-x1) * (y2 - y1) - (lat - y1) * (x2 - x1)
        if abs(cross) <= 1e-10 and min(x1, x2)-1e-9 <= 0 <= max(x1,x2)+1e-9 and min(y1,y2)-1e-9 <= lat <= max(y1,y2)+1e-9:
            return True
        if (y1 > lat) != (y2 > lat):
            intersect = x1 + (x2 - x1) * (lat - y1) / (y2 - y1)
            if intersect > 0:
                inside = not inside
    return inside

def area_ha(ring):
    """Approximate spherical polygon area in hectares, with dateline unwrapping."""
    if len(ring) < 3:
        return 0.0
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(ring, ring[1:] + ring[:1]):
        delta = math.radians(_delta_lon(lon2, lon1))
        total += delta * (math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))
    return round(abs(total) * EARTH_RADIUS_M**2 / 2.0 / 10000.0, 2)
