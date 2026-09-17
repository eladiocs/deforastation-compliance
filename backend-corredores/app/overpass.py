"""Live Overpass API client for OSM land-cover/way data, used by terrain.py.
Responses are cached to disk keyed by query hash (backend/cache/<sha1>.json)
so repeated analyses over the same area don't re-hit Overpass, and analysis
can still work offline once an area has been queried once."""

import hashlib
import json
import time
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import LineString, MultiPolygon, Polygon

from .config import settings

# Public Overpass instances get overloaded and return 502/503/504/429 fairly
# often. OSM is a secondary source now (see terrain.py — ESA WorldCover is
# primary), so we'd rather fail fast and fall through to the next mirror than
# retry-with-backoff against one that's struggling: worst case here is 3
# mirrors x REQUEST_TIMEOUT_S ~= 24s per Overpass query, and a full analysis
# makes at most a handful of these — the whole request must never make a user
# wait more than ~2 minutes.
OVERPASS_URLS = [
    settings.OVERPASS_URL,
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
REQUEST_TIMEOUT_S = 8
RETRIES_PER_URL = 1
RETRY_BACKOFF_S = 2.0
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
# overpass-api.de returns 406 Not Acceptable for requests' default
# "python-requests/x.x" User-Agent; send an explicit one instead.
REQUEST_HEADERS = {"User-Agent": "bioconnect-app/1.0 (+https://github.com/bioconnect)"}

AREAS_TAGS = ["natural", "landuse", "leisure"]
LINES_TAGS = ["highway", "waterway"]


def _bbox_str(bbox_wgs84: tuple[float, float, float, float]) -> str:
    west, south, east, north = bbox_wgs84
    return f"{south},{west},{north},{east}"


def _build_query(bbox_wgs84: tuple[float, float, float, float], tags: list[str], include_relations: bool) -> str:
    bbox = _bbox_str(bbox_wgs84)
    clauses = [f'way["{tag}"]({bbox});' for tag in tags]
    if include_relations:
        clauses += [f'relation["{tag}"]({bbox});' for tag in tags]
    return f"[out:json][timeout:{REQUEST_TIMEOUT_S}];\n(\n  " + "\n  ".join(clauses) + "\n);\nout geom;"


def _query_one_url(url: str, query: str) -> dict:
    last_exc: Exception | None = None
    for attempt in range(RETRIES_PER_URL):
        if attempt > 0:
            time.sleep(RETRY_BACKOFF_S * attempt)
        try:
            response = requests.post(
                url, data={"data": query}, timeout=REQUEST_TIMEOUT_S, headers=REQUEST_HEADERS
            )
            if response.status_code in RETRYABLE_STATUS_CODES:
                last_exc = requests.HTTPError(f"{response.status_code} from {url}", response=response)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def _query_overpass(query: str) -> dict:
    cache_path = CACHE_DIR / f"{hashlib.sha1(query.encode()).hexdigest()}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    last_exc: Exception | None = None
    for url in OVERPASS_URLS:
        try:
            data = _query_one_url(url, query)
            break
        except requests.RequestException as exc:
            last_exc = exc
    else:
        assert last_exc is not None
        raise last_exc

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data), encoding="utf-8")
    return data


def _ring_from_geometry(geometry: list[dict]) -> list[tuple[float, float]] | None:
    if len(geometry) < 4:
        return None
    ring = [(pt["lon"], pt["lat"]) for pt in geometry]
    if ring[0] != ring[-1]:
        return None
    return ring


def _way_to_polygon(element: dict) -> Polygon | None:
    ring = _ring_from_geometry(element.get("geometry") or [])
    if ring is None:
        return None
    try:
        polygon = Polygon(ring)
    except Exception:
        return None
    return polygon if polygon.is_valid and not polygon.is_empty else None


def _relation_to_polygon(element: dict) -> Polygon | MultiPolygon | None:
    outer_rings, inner_rings = [], []
    for member in element.get("members", []):
        if member.get("type") != "way" or not member.get("geometry"):
            continue
        ring = _ring_from_geometry(member["geometry"])
        if ring is None:
            continue
        (outer_rings if member.get("role") != "inner" else inner_rings).append(ring)

    if not outer_rings:
        return None
    try:
        if len(outer_rings) == 1:
            polygon = Polygon(outer_rings[0], holes=inner_rings)
        else:
            polygon = MultiPolygon([Polygon(outer) for outer in outer_rings])
    except Exception:
        return None
    return polygon if polygon.is_valid and not polygon.is_empty else None


def fetch_areas(bbox_wgs84: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Fetches natural/landuse/leisure areas (ways + multipolygon relations) for
    a bbox from Overpass, as polygons with their OSM tags in EPSG:4326."""
    query = _build_query(bbox_wgs84, AREAS_TAGS, include_relations=True)
    data = _query_overpass(query)

    rows, geometries = [], []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        if element.get("type") == "way":
            geom = _way_to_polygon(element)
        elif element.get("type") == "relation":
            geom = _relation_to_polygon(element)
        else:
            geom = None
        if geom is None:
            continue
        rows.append({"natural": tags.get("natural"), "landuse": tags.get("landuse"),
                      "leisure": tags.get("leisure"), "name": tags.get("name")})
        geometries.append(geom)

    if not geometries:
        return gpd.GeoDataFrame({"natural": [], "landuse": [], "leisure": [], "name": []}, geometry=[], crs="EPSG:4326")
    return gpd.GeoDataFrame(rows, geometry=geometries, crs="EPSG:4326")


def fetch_lines(bbox_wgs84: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Fetches highway/waterway ways for a bbox from Overpass, as linestrings
    with their OSM tags in EPSG:4326."""
    query = _build_query(bbox_wgs84, LINES_TAGS, include_relations=False)
    data = _query_overpass(query)

    rows, geometries = [], []
    for element in data.get("elements", []):
        geometry = element.get("geometry") or []
        if len(geometry) < 2:
            continue
        tags = element.get("tags", {})
        rows.append({"highway": tags.get("highway"), "waterway": tags.get("waterway")})
        geometries.append(LineString([(pt["lon"], pt["lat"]) for pt in geometry]))

    if not geometries:
        return gpd.GeoDataFrame({"highway": [], "waterway": []}, geometry=[], crs="EPSG:4326")
    return gpd.GeoDataFrame(rows, geometry=geometries, crs="EPSG:4326")
