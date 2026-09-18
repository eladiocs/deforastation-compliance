"""Real land-cover-based resistance surface + least-cost path, replacing the
placeholder hash-based resistance in graph_service.py with data pulled live
from two sources: ESA WorldCover satellite land cover (see worldcover.py),
the primary/trusted classification, layered with OpenStreetMap data via
Overpass (see overpass.py) for place names and precise road/waterway
barriers. Both sources are cached to disk per bbox query, so repeated
analyses over the same area don't re-hit either API."""

import logging
import math
from dataclasses import dataclass
from functools import lru_cache

import geopandas as gpd
import numpy as np
import pandas as pd
from affine import Affine
from pyproj import Transformer
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from . import overpass, worldcover
from .config import settings

logger = logging.getLogger(__name__)

HABITAT_TAGS = {
    "natural": ["wood", "grassland", "scrub", "heath"],
    "landuse": ["forest", "meadow", "grass"],
    "leisure": ["park", "garden", "nature_reserve"],
}

WATER_RESISTANCE = 100.0
DEFAULT_RESISTANCE = 8.0
FOOTPRINT_RESISTANCE = 500.0  # project footprint acting as a near-impassable barrier

NATURAL_RESISTANCE = {
    "water": WATER_RESISTANCE,
    "wetland": 60.0,
    "wood": 1.0,
    "grassland": 2.0,
    "scrub": 3.0,
    "heath": 3.0,
    "beach": 5.0,
    "sand": 8.0,
}
LANDUSE_RESISTANCE = {
    "forest": 1.0,
    "grass": 2.0,
    "meadow": 2.0,
    "farmland": 5.0,
    "farmyard": 6.0,
    "cemetery": 8.0,
    "residential": 20.0,
    "commercial": 25.0,
    "retail": 25.0,
    "industrial": 30.0,
}
LEISURE_RESISTANCE = {
    "park": 2.0,
    "garden": 2.0,
    "nature_reserve": 1.0,
    "golf_course": 4.0,
    "pitch": 5.0,
}
MAJOR_HIGHWAY_VALUES = {"motorway", "trunk", "primary", "motorway_link", "trunk_link", "primary_link"}
MAJOR_HIGHWAY_RESISTANCE = 200.0  # near-impassable for terrestrial mammals without a dedicated crossing
MINOR_HIGHWAY_RESISTANCE = 15.0
MAJOR_HIGHWAY_BUFFER_M = 30.0  # carriageways + median + shoulders + fencing
MINOR_HIGHWAY_BUFFER_M = 4.0
WATERWAY_BUFFER_M = 6.0

_MAX_GRID_DIM = 300  # caps grid cells at ~300x300 regardless of bbox size

_WGS84_TO_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
_MERCATOR_TO_WGS84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def to_mercator(lat: float, lng: float) -> tuple[float, float]:
    return _WGS84_TO_MERCATOR.transform(lng, lat)


def to_wgs84(x: float, y: float) -> tuple[float, float]:
    lng, lat = _MERCATOR_TO_WGS84.transform(x, y)
    return lat, lng


def _round_bbox(bbox_wgs84: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    west, south, east, north = bbox_wgs84
    round_to = 1e-4  # ~11m
    return (
        math.floor(west / round_to) * round_to,
        math.floor(south / round_to) * round_to,
        math.ceil(east / round_to) * round_to,
        math.ceil(north / round_to) * round_to,
    )


def _area_resistance(row) -> float | None:
    natural = row.get("natural")
    if isinstance(natural, str) and natural in NATURAL_RESISTANCE:
        return NATURAL_RESISTANCE[natural]
    landuse = row.get("landuse")
    if isinstance(landuse, str) and landuse in LANDUSE_RESISTANCE:
        return LANDUSE_RESISTANCE[landuse]
    leisure = row.get("leisure")
    if isinstance(leisure, str) and leisure in LEISURE_RESISTANCE:
        return LEISURE_RESISTANCE[leisure]
    return None


def _line_resistance_and_buffer(row) -> tuple[float, float] | None:
    waterway = row.get("waterway")
    if isinstance(waterway, str):
        return WATER_RESISTANCE, WATERWAY_BUFFER_M
    highway = row.get("highway")
    if isinstance(highway, str):
        if highway in MAJOR_HIGHWAY_VALUES:
            return MAJOR_HIGHWAY_RESISTANCE, MAJOR_HIGHWAY_BUFFER_M
        return MINOR_HIGHWAY_RESISTANCE, MINOR_HIGHWAY_BUFFER_M
    return None


@lru_cache(maxsize=64)
def _fetch_land_cover_cached(west: float, south: float, east: float, north: float) -> gpd.GeoDataFrame:
    """Fetches OSM land cover for a bbox live from Overpass and returns
    polygons with a `resistance` column, reprojected to EPSG:3857 (meters).
    Cached per rounded bbox so repeated analyses over the same area don't
    re-hit the API within this process's lifetime (overpass.py also caches
    the raw response to disk, across restarts)."""
    bbox = (west, south, east, north)
    geometries_3857: list = []
    resistances: list[float] = []

    areas = overpass.fetch_areas(bbox)
    if len(areas):
        areas = areas[areas.geom_type.isin(["Polygon", "MultiPolygon"])]
        if len(areas):
            areas_3857 = areas.to_crs(epsg=3857)
            for (_, row), geom_3857 in zip(areas.iterrows(), areas_3857.geometry):
                resistance = _area_resistance(row)
                if resistance is not None:
                    geometries_3857.append(geom_3857)
                    resistances.append(resistance)

    lines = overpass.fetch_lines(bbox)
    if len(lines):
        lines = lines[lines.geom_type.isin(["LineString", "MultiLineString"])]
        if len(lines):
            lines_3857 = lines.to_crs(epsg=3857)
            for (_, row), geom_3857 in zip(lines.iterrows(), lines_3857.geometry):
                classified = _line_resistance_and_buffer(row)
                if classified is not None:
                    resistance, buffer_m = classified
                    geometries_3857.append(geom_3857.buffer(buffer_m))
                    resistances.append(resistance)

    if not geometries_3857:
        return gpd.GeoDataFrame({"resistance": []}, geometry=[], crs="EPSG:3857")

    return gpd.GeoDataFrame({"resistance": resistances}, geometry=geometries_3857, crs="EPSG:3857")


def bbox_3857_to_wgs84(bbox_3857: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    xmin, ymin, xmax, ymax = bbox_3857
    west, south = _MERCATOR_TO_WGS84.transform(xmin, ymin)
    east, north = _MERCATOR_TO_WGS84.transform(xmax, ymax)
    return west, south, east, north


def fetch_land_cover(bbox_wgs84: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    return _fetch_land_cover_cached(*_round_bbox(bbox_wgs84))


def add_barrier(land_cover: gpd.GeoDataFrame, barrier_geom, resistance: float) -> gpd.GeoDataFrame:
    """Appends `barrier_geom` (already in EPSG:3857) as one more land-cover row so
    build_resistance_grid's existing max-resistance-wins sjoin treats it as an
    additional resistance source — e.g. a project footprint acting as a barrier
    to dispersal — with no changes needed to build_resistance_grid itself."""
    barrier_row = gpd.GeoDataFrame({"resistance": [resistance]}, geometry=[barrier_geom], crs="EPSG:3857")
    if len(land_cover) == 0:
        return barrier_row
    return gpd.GeoDataFrame(
        pd.concat([land_cover[["resistance", "geometry"]], barrier_row], ignore_index=True),
        crs="EPSG:3857",
    )


def _is_habitat(row) -> bool:
    for key, allowed_values in HABITAT_TAGS.items():
        value = row.get(key)
        if isinstance(value, str) and value in allowed_values:
            return True
    return False


@lru_cache(maxsize=64)
def _fetch_habitat_polygons_cached(west: float, south: float, east: float, north: float) -> gpd.GeoDataFrame:
    """Fetches real green-space polygons (parks, forests, nature reserves) for
    a bbox live from Overpass, reprojected to EPSG:3857 (meters) for
    area/centroid math. A failed fetch raises — that's a real error, not "no
    habitat here" — and since lru_cache only memoizes successful returns, a
    failed fetch is never cached, so a retry can succeed once fixed."""
    features = overpass.fetch_areas((west, south, east, north))
    if not len(features):
        return gpd.GeoDataFrame({"name": []}, geometry=[], crs="EPSG:3857")

    features = features[features.geom_type.isin(["Polygon", "MultiPolygon"])]
    features = features[features.apply(_is_habitat, axis=1)]
    if not len(features):
        return gpd.GeoDataFrame({"name": []}, geometry=[], crs="EPSG:3857")

    features_3857 = features.to_crs(epsg=3857)
    names = features["name"] if "name" in features.columns else [None] * len(features)
    return gpd.GeoDataFrame({"name": list(names)}, geometry=list(features_3857.geometry), crs="EPSG:3857")


def fetch_habitat_polygons(bbox_wgs84: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Habitat polygons for the connectivity graph. ESA WorldCover (10m
    satellite land cover, see worldcover.py) is the primary/trusted source:
    OSM tagging alone misses real habitat that was simply never drawn as a
    natural=wood/landuse=forest/etc. polygon. OSM still contributes what it
    does well: real place names, and any small green space (e.g. an urban
    garden) that WorldCover's 10m resolution classifies as built-up and
    therefore misses."""
    osm = _fetch_habitat_polygons_cached(*_round_bbox(bbox_wgs84))

    wc = None
    if settings.WORLDCOVER_ENABLED:
        try:
            wc = worldcover.fetch_habitat_polygons(bbox_wgs84)
        except Exception:
            logger.warning("WorldCover habitat fetch failed for %s; falling back to OSM-only habitat", bbox_wgs84, exc_info=True)

    if wc is None or not len(wc):
        return osm
    if not len(osm):
        return wc

    named_osm = osm[osm["name"].apply(lambda n: isinstance(n, str) and n.strip() != "")]
    if len(named_osm):
        wc_indexed = wc[["geometry"]].reset_index(drop=True).rename_axis("wc_idx").reset_index()
        pairs = gpd.overlay(
            named_osm[["name", "geometry"]].reset_index(drop=True),
            wc_indexed,
            how="intersection",
            keep_geom_type=False,
        )
        if len(pairs):
            pairs["overlap_area"] = pairs.geometry.area
            best = pairs.loc[pairs.groupby("wc_idx")["overlap_area"].idxmax()]
            name_by_wc_idx = dict(zip(best["wc_idx"], best["name"]))
            wc = wc.reset_index(drop=True)
            wc["name"] = [name_by_wc_idx.get(i) for i in range(len(wc))]

    covered = wc.geometry.union_all()
    uncovered_osm = osm[~osm.geometry.intersects(covered)]

    return pd.concat([wc, uncovered_osm], ignore_index=True)


@dataclass
class ResistanceGrid:
    resistance: np.ndarray  # shape (n_rows, n_cols)
    xmin: float
    ymin: float
    cell_size: float

    @property
    def n_rows(self) -> int:
        return self.resistance.shape[0]

    @property
    def n_cols(self) -> int:
        return self.resistance.shape[1]

    def xy_to_cell(self, x: float, y: float) -> tuple[int, int]:
        col = int(min(max((x - self.xmin) / self.cell_size, 0), self.n_cols - 1))
        row = int(min(max((y - self.ymin) / self.cell_size, 0), self.n_rows - 1))
        return row, col

    def cell_center(self, row: int, col: int) -> tuple[float, float]:
        return (self.xmin + (col + 0.5) * self.cell_size, self.ymin + (row + 0.5) * self.cell_size)


def build_resistance_grid(
    bbox_3857: tuple[float, float, float, float],
    land_cover: gpd.GeoDataFrame,
    cell_size: float = 25.0,
) -> ResistanceGrid:
    xmin, ymin, xmax, ymax = bbox_3857
    width, height = xmax - xmin, ymax - ymin
    cell_size = max(cell_size, max(width, height) / _MAX_GRID_DIM)

    n_cols = max(1, math.ceil(width / cell_size))
    n_rows = max(1, math.ceil(height / cell_size))

    resistance = _worldcover_base_grid(bbox_3857, n_rows, n_cols, cell_size)

    if len(land_cover):
        xs = xmin + (np.arange(n_cols) + 0.5) * cell_size
        ys = ymin + (np.arange(n_rows) + 0.5) * cell_size
        xx, yy = np.meshgrid(xs, ys)
        points = gpd.GeoDataFrame(
            {"row": np.repeat(np.arange(n_rows), n_cols), "col": np.tile(np.arange(n_cols), n_rows)},
            geometry=gpd.points_from_xy(xx.ravel(), yy.ravel()),
            crs="EPSG:3857",
        )
        joined = gpd.sjoin(points, land_cover[["resistance", "geometry"]], predicate="intersects", how="inner")
        if len(joined):
            best = joined.groupby(["row", "col"])["resistance"].max()
            rows_idx = best.index.get_level_values("row").to_numpy()
            cols_idx = best.index.get_level_values("col").to_numpy()
            # Base layer is now WorldCover-derived (not a flat constant), so an
            # OSM tag with a *lower* resistance than the satellite value must
            # not "downgrade" it — only ever raise resistance towards a hard
            # barrier (roads, water, the project footprint).
            resistance[rows_idx, cols_idx] = np.maximum(resistance[rows_idx, cols_idx], best.to_numpy())

    return ResistanceGrid(resistance=resistance, xmin=xmin, ymin=ymin, cell_size=cell_size)


def _worldcover_base_grid(
    bbox_3857: tuple[float, float, float, float], n_rows: int, n_cols: int, cell_size: float
) -> np.ndarray:
    if not settings.WORLDCOVER_ENABLED:
        return np.full((n_rows, n_cols), DEFAULT_RESISTANCE)
    try:
        xmin, ymin, _, _ = bbox_3857
        dst_transform = Affine(cell_size, 0, xmin, 0, cell_size, ymin)
        bbox_wgs84 = bbox_3857_to_wgs84(bbox_3857)
        return worldcover.resistance_grid_3857(bbox_wgs84, dst_transform, (n_rows, n_cols), DEFAULT_RESISTANCE)
    except Exception:
        logger.warning("WorldCover base resistance grid failed for %s; falling back to flat default", bbox_3857, exc_info=True)
        return np.full((n_rows, n_cols), DEFAULT_RESISTANCE)


def _build_adjacency(grid: ResistanceGrid) -> csr_matrix:
    n_rows, n_cols = grid.n_rows, grid.n_cols
    n = n_rows * n_cols
    node_id = np.arange(n).reshape(n_rows, n_cols)
    resistance = grid.resistance

    src_ids, dst_ids, weights = [], [], []
    for dr, dc in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
        dist = grid.cell_size * math.hypot(dr, dc)
        src_r0, src_r1 = max(0, -dr), n_rows - max(0, dr)
        src_c0, src_c1 = max(0, -dc), n_cols - max(0, dc)
        dst_r0, dst_r1 = max(0, dr), n_rows - max(0, -dr)
        dst_c0, dst_c1 = max(0, dc), n_cols - max(0, -dc)

        src = node_id[src_r0:src_r1, src_c0:src_c1].ravel()
        dst = node_id[dst_r0:dst_r1, dst_c0:dst_c1].ravel()
        src_res = resistance[src_r0:src_r1, src_c0:src_c1].ravel()
        dst_res = resistance[dst_r0:dst_r1, dst_c0:dst_c1].ravel()

        src_ids.append(src)
        dst_ids.append(dst)
        weights.append((src_res + dst_res) / 2 * dist)

    rows = np.concatenate(src_ids)
    cols = np.concatenate(dst_ids)
    data = np.concatenate(weights)
    return csr_matrix((data, (rows, cols)), shape=(n, n))


def least_cost_path(
    grid: ResistanceGrid, start_lat: float, start_lng: float, end_lat: float, end_lng: float
) -> tuple[list[tuple[float, float]], float]:
    start_x, start_y = _WGS84_TO_MERCATOR.transform(start_lng, start_lat)
    end_x, end_y = _WGS84_TO_MERCATOR.transform(end_lng, end_lat)
    start_row, start_col = grid.xy_to_cell(start_x, start_y)
    end_row, end_col = grid.xy_to_cell(end_x, end_y)
    start_id = start_row * grid.n_cols + start_col
    end_id = end_row * grid.n_cols + end_col

    graph = _build_adjacency(grid)
    dist_matrix, predecessors = dijkstra(graph, directed=True, indices=start_id, return_predecessors=True)

    if not math.isfinite(dist_matrix[end_id]):
        return [(start_lat, start_lng), (end_lat, end_lng)], float("inf")

    path_ids = [end_id]
    node = end_id
    while node != start_id:
        node = predecessors[node]
        if node < 0:
            return [(start_lat, start_lng), (end_lat, end_lng)], float("inf")
        path_ids.append(node)
    path_ids.reverse()

    xs, ys = [], []
    for node_idx in path_ids:
        row, col = divmod(node_idx, grid.n_cols)
        x, y = grid.cell_center(row, col)
        xs.append(x)
        ys.append(y)
    lngs, lats = _MERCATOR_TO_WGS84.transform(xs, ys)
    route = list(zip(lats, lngs))
    return route, float(dist_matrix[end_id])
