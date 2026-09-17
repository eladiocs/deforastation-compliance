"""Live ESA WorldCover (v200, 2021, 10m) land-cover source, read directly from
the public AWS S3 Cloud-Optimized GeoTIFFs via GDAL's /vsicurl/ virtual
filesystem — no download, no auth. This is the *primary/trusted* habitat and
resistance classification: OSM tagging alone (terrain.py's HABITAT_TAGS) is
incomplete, so real forest/park areas that were never drawn as an explicit
natural=wood/landuse=forest/etc. polygon in OSM were previously invisible to
the whole analysis. terrain.py still layers OSM on top for what it does
well: real place names, and precise road/waterway barriers (10m satellite
classification often mistakes tree canopy over a road for forest)."""

import hashlib
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from affine import Affine
from rasterio.features import shapes
from rasterio.merge import merge
from rasterio.warp import Resampling, reproject
from scipy.ndimage import binary_opening
from shapely.geometry import shape

from .config import settings

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "worldcover"

TILE_DEG = 3
NODATA = 0  # WorldCover class codes are all >= 10; 0 is safe to use as "no data" fill

CLASS_RESISTANCE: dict[int, float] = {
    10: 1.0,  # Tree cover                 -- matches terrain.NATURAL_RESISTANCE["wood"]
    20: 3.0,  # Shrubland                   -- matches "scrub"/"heath"
    30: 2.0,  # Grassland                   -- matches "grassland"/"grass"/"meadow"
    40: 5.0,  # Cropland                    -- matches "farmland"
    50: 20.0,  # Built-up                   -- matches "residential"
    60: 8.0,  # Bare / sparse vegetation    -- matches "sand"
    70: 80.0,  # Snow and ice               -- near-impassable but not open water
    80: 100.0,  # Permanent water bodies    -- matches terrain.WATER_RESISTANCE
    90: 60.0,  # Herbaceous wetland         -- matches "wetland"
    95: 2.5,  # Mangroves                   -- high-value habitat, but waterlogged/prop-root
    #      substrate adds real friction beyond dry forest
    100: 6.0,  # Moss and lichen           -- sparse cover, poor habitat
}

# Classes counted as habitat for patch generation. Deliberately broader than
# terrain.HABITAT_TAGS (which never covered wetlands/mangroves) — relevant
# ecological habitat for biological-corridor analysis, not just "green".
HABITAT_CLASSES = {10, 20, 30, 90, 95}

_RESISTANCE_LUT = np.full(256, np.nan, dtype=np.float64)
for _code, _value in CLASS_RESISTANCE.items():
    _RESISTANCE_LUT[_code] = _value


def resistance_for_classes(classes: np.ndarray, default: float) -> np.ndarray:
    """Vectorized class-code -> resistance lookup. Unmapped codes (including
    NODATA=0, i.e. no tile coverage) fall back to `default`."""
    looked_up = _RESISTANCE_LUT[classes]
    return np.where(np.isnan(looked_up), default, looked_up)


def _tile_id(tile_lat: float, tile_lon: float) -> str:
    lat_hem = "N" if tile_lat >= 0 else "S"
    lon_hem = "E" if tile_lon >= 0 else "W"
    return f"{lat_hem}{abs(int(tile_lat)):02d}{lon_hem}{abs(int(tile_lon)):03d}"


def _tile_ids_for_bbox(bbox_wgs84: tuple[float, float, float, float]) -> list[str]:
    west, south, east, north = bbox_wgs84
    lats = {math.floor(south / TILE_DEG) * TILE_DEG, math.floor(north / TILE_DEG) * TILE_DEG}
    lons = {math.floor(west / TILE_DEG) * TILE_DEG, math.floor(east / TILE_DEG) * TILE_DEG}
    return sorted(_tile_id(tile_lat, tile_lon) for tile_lat in lats for tile_lon in lons)


def _tile_url(tile_id: str) -> str:
    return f"{settings.WORLDCOVER_BASE_URL}/ESA_WorldCover_10m_2021_v200_{tile_id}_Map.tif"


def _round_bbox(bbox_wgs84: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    # Intentionally mirrors terrain._round_bbox so cache keys stay stable;
    # duplicated (not imported) to avoid a circular import with terrain.py.
    west, south, east, north = bbox_wgs84
    round_to = 1e-4  # ~11m
    return (
        math.floor(west / round_to) * round_to,
        math.floor(south / round_to) * round_to,
        math.ceil(east / round_to) * round_to,
        math.ceil(north / round_to) * round_to,
    )


def _fetch_classes_wgs84(bbox_wgs84: tuple[float, float, float, float]) -> tuple[np.ndarray, Affine]:
    """Reads raw WorldCover class codes for bbox_wgs84 straight from S3 (no
    cache), merging tiles when the bbox straddles a tile boundary. Returns a
    uint8 array + its EPSG:4326 affine transform."""
    urls = [_tile_url(tile_id) for tile_id in _tile_ids_for_bbox(bbox_wgs84)]
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        sources = [rasterio.open(f"/vsicurl/{url}") for url in urls]
        try:
            array, transform = merge(sources, bounds=bbox_wgs84, nodata=NODATA, res=sources[0].res)
        finally:
            for source in sources:
                source.close()
    return array[0].astype(np.uint8), transform


def _cache_path(bbox_wgs84: tuple[float, float, float, float]) -> Path:
    key = ":".join(f"{v:.6f}" for v in bbox_wgs84)
    digest = hashlib.sha1(key.encode()).hexdigest()
    return CACHE_DIR / f"{digest}.npz"


def _fetch_classes_wgs84_cached(bbox_wgs84: tuple[float, float, float, float]) -> tuple[np.ndarray, Affine]:
    rounded = _round_bbox(bbox_wgs84)
    path = _cache_path(rounded)
    if path.exists():
        with np.load(path) as data:
            return data["classes"], Affine(*data["transform"])

    classes, transform = _fetch_classes_wgs84(rounded)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, classes=classes, transform=np.array(tuple(transform)[:6]))
    return classes, transform


def resistance_grid_3857(
    bbox_wgs84: tuple[float, float, float, float],
    dst_transform: Affine,
    dst_shape: tuple[int, int],
    default_resistance: float,
) -> np.ndarray:
    """Resamples WorldCover classes onto an arbitrary EPSG:3857 grid (matching
    terrain.ResistanceGrid's cell layout) and returns the resistance value per
    cell — the base layer terrain.build_resistance_grid fills before OSM
    roads/waterways/footprint are layered on top."""
    classes_4326, transform_4326 = _fetch_classes_wgs84_cached(bbox_wgs84)
    dst_classes = np.zeros(dst_shape, dtype=np.uint8)
    reproject(
        source=classes_4326,
        destination=dst_classes,
        src_transform=transform_4326,
        src_crs="EPSG:4326",
        dst_transform=dst_transform,
        dst_crs="EPSG:3857",
        resampling=Resampling.nearest,
    )
    return resistance_for_classes(dst_classes, default_resistance)


def fetch_habitat_polygons(bbox_wgs84: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Vectorizes WorldCover's habitat classes into polygons, in the same
    shape terrain.fetch_habitat_polygons returns (columns `name` — always
    None here, WorldCover carries no names — and `geometry`, EPSG:3857)."""
    empty = gpd.GeoDataFrame({"name": []}, geometry=[], crs="EPSG:3857")

    classes, transform = _fetch_classes_wgs84_cached(bbox_wgs84)
    mask = np.isin(classes, list(HABITAT_CLASSES))
    if not mask.any():
        return empty

    # 10m satellite classification is noisier than hand-drawn OSM polygons;
    # strip single/double-pixel speckle before vectorizing.
    mask = binary_opening(mask, structure=np.ones((3, 3), dtype=bool))
    if not mask.any():
        return empty

    geometries = [
        shape(geom)
        for geom, value in shapes(mask.astype(np.uint8), mask=mask, connectivity=8, transform=transform)
        if value == 1
    ]
    if not geometries:
        return empty

    gdf = gpd.GeoDataFrame({"name": [None] * len(geometries)}, geometry=geometries, crs="EPSG:4326")
    return gdf.to_crs(epsg=3857)
