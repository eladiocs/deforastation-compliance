import math
from itertools import combinations

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, Polygon, box

from . import terrain
from .models import (
    CorridorEdge,
    GraphMetrics,
    GraphResponse,
    ImpactAnalysisResult,
    LatLngPoint,
    Patch,
    ShortestPathResult,
    TopCorridor,
)

MIN_HABITAT_AREA_M2 = 400.0
MIN_PATCH_RADIUS_M = 15.0
MAX_PATCH_RADIUS_M = 300.0
# A habitat polygon bigger than one clamped patch circle (WorldCover routinely
# produces these — e.g. a whole park as one contiguous polygon, vs. OSM's
# smaller hand-drawn ones) would otherwise collapse into a single unrealistic
# circle at one arbitrary point. Above this area it gets split into a grid of
# sub-patches instead (see _split_large_geom).
MAX_PATCH_AREA_M2 = math.pi * MAX_PATCH_RADIUS_M**2
SPLIT_CELL_M = 2 * MAX_PATCH_RADIUS_M


def _edge_key(a: str, b: str) -> str:
    return f"{a}|{b}" if a < b else f"{b}|{a}"


def _same_source_edge_keys(source_groups: dict[str, str]) -> set[str]:
    """All patch-pair keys that share a source polygon (see generate_study_area
    / build_corridors), so analyze_graph can hide them from the "corredores"
    the map/report show, while still using them to compute true connectivity."""
    by_group: dict[str, list[str]] = {}
    for patch_id, group in source_groups.items():
        by_group.setdefault(group, []).append(patch_id)
    return {
        _edge_key(a, b)
        for ids in by_group.values()
        for i, a in enumerate(ids)
        for b in ids[i + 1 :]
    }


def patches_to_geoframe(patches: list[Patch]) -> gpd.GeoDataFrame:
    """Builds a GeoDataFrame in Web Mercator (EPSG:3857, meters) so planar
    distance on the geometries approximates real-world distance. Patches
    are stored as lat/lng (EPSG:4326); this reprojects for the math only."""
    gdf = gpd.GeoDataFrame(
        {"id": [p.id for p in patches], "name": [p.name for p in patches]},
        geometry=[Point(p.lng, p.lat) for p in patches],
        crs="EPSG:4326",
    )
    return gdf.to_crs(epsg=3857)


def build_corridors(
    patches: list[Patch],
    max_distance: float,
    footprint_3857=None,
    footprint_resistance: float = terrain.FOOTPRINT_RESISTANCE,
    source_groups: dict[str, str] | None = None,
    land_cover_bbox_3857: tuple[float, float, float, float] | None = None,
) -> list[CorridorEdge]:
    if len(patches) < 2:
        return []

    source_groups = source_groups or {}
    gdf = patches_to_geoframe(patches)
    if land_cover_bbox_3857 is not None:
        # Passed in by analyze_impact so the baseline and scenario calls share
        # the exact same bbox: scenario_patches is always a subset of
        # baseline_patches, so the baseline bbox already covers it, and
        # reusing it hits terrain's in-memory OSM/WorldCover caches instead of
        # re-querying Overpass for a near-identical area a second time.
        bbox_3857 = land_cover_bbox_3857
    else:
        margin = max(max_distance, 200.0)
        minx, miny, maxx, maxy = gdf.total_bounds
        bbox_3857 = (minx - margin, miny - margin, maxx + margin, maxy + margin)
    land_cover = terrain.fetch_land_cover(terrain.bbox_3857_to_wgs84(bbox_3857))
    if footprint_3857 is not None:
        land_cover = terrain.add_barrier(land_cover, footprint_3857, footprint_resistance)

    # No real land-cover data (OSM unreachable, or genuinely nothing there): skip
    # building the grid and running Dijkstra, since with uniform resistance the
    # least-cost path is already just the straight line between the two patches.
    has_real_terrain = len(land_cover) > 0
    grid = terrain.build_resistance_grid(bbox_3857, land_cover) if has_real_terrain else None

    edges: list[CorridorEdge] = []
    for i, j in combinations(range(len(patches)), 2):
        distance = gdf.geometry.iloc[i].distance(gdf.geometry.iloc[j])
        a, b = patches[i], patches[j]
        # Patches split from the same oversized source polygon (_split_large_geom)
        # are pieces of one contiguous habitat block, not separate fragments
        # needing dispersal — always connect them regardless of max_distance,
        # with a low nominal cost (no real barrier to cross between them),
        # instead of running them through the distance-gated dispersal logic
        # below, which would otherwise report them as unreachable from each
        # other whenever the spread-out split points land further apart than
        # the dispersal distance.
        same_source = a.id in source_groups and source_groups[a.id] == source_groups.get(b.id)
        if same_source:
            edges.append(
                CorridorEdge(
                    source=a.id,
                    target=b.id,
                    distance=distance,
                    resistance=1.0,
                    cost=distance,
                    route=[LatLngPoint(lat=a.lat, lng=a.lng), LatLngPoint(lat=b.lat, lng=b.lng)],
                )
            )
            continue
        if distance <= max_distance:
            if grid is not None:
                route, cost = terrain.least_cost_path(grid, a.lat, a.lng, b.lat, b.lng)
            else:
                cost = distance * terrain.DEFAULT_RESISTANCE
                route = [(a.lat, a.lng), (b.lat, b.lng)]
            edges.append(
                CorridorEdge(
                    source=a.id,
                    target=b.id,
                    distance=distance,
                    resistance=cost / distance if distance else 0.0,
                    cost=cost,
                    route=[LatLngPoint(lat=lat, lng=lng) for lat, lng in route],
                )
            )
    return edges


def build_graph(patches: list[Patch], edges: list[CorridorEdge]) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(p.id for p in patches)
    for e in edges:
        graph.add_edge(e.source, e.target, weight=e.cost)
    return graph


def analyze_graph(
    patches: list[Patch], edges: list[CorridorEdge], hidden_edge_keys: set[str] | None = None
) -> tuple[list[CorridorEdge], GraphMetrics]:
    """Runs connectivity analysis once and returns edges annotated with their
    betweenness score alongside the aggregate metrics, so callers never need
    to recompute centrality twice for the same graph.

    `hidden_edge_keys` marks edges that are connectivity-true but not real
    dispersal corridors (see build_corridors' same-source handling: sub-patches
    split from one contiguous habitat polygon are always connected to each
    other, since there's no real gap between them to disperse across). Those
    edges still count towards components/fragmentation/isolation below — that
    part must reflect they're genuinely connected — but they're excluded from
    what's returned and counted as "corredores", so the map/report don't draw
    a fake corridor criss-crossing a single forest block, or list it as "cut"
    every time one sub-patch is destroyed."""
    hidden_edge_keys = hidden_edge_keys or set()
    graph = build_graph(patches, edges)
    components = list(nx.connected_components(graph))
    largest = max((len(c) for c in components), default=0)
    isolated_ids = [next(iter(c)) for c in components if len(c) == 1]
    fragmentation = 0.0 if not patches else 1 - largest / len(patches)

    edge_betweenness = (
        nx.edge_betweenness_centrality(graph, weight="weight") if graph.number_of_edges() else {}
    )
    score_by_key = {_edge_key(u, v): score for (u, v), score in edge_betweenness.items()}
    visible_edges = [e for e in edges if _edge_key(e.source, e.target) not in hidden_edge_keys]
    annotated_edges = [
        e.model_copy(update={"betweenness": score_by_key.get(_edge_key(e.source, e.target), 0.0)})
        for e in visible_edges
    ]

    top_corridors = sorted(
        (TopCorridor(edge=e, betweenness=e.betweenness) for e in annotated_edges),
        key=lambda t: t.betweenness,
        reverse=True,
    )[:5]

    metrics = GraphMetrics(
        total_patches=len(patches),
        total_corridors=len(annotated_edges),
        component_count=len(components),
        isolated_patch_ids=isolated_ids,
        largest_component_size=largest,
        fragmentation_index=fragmentation,
        top_corridors=top_corridors,
    )
    return annotated_edges, metrics


def shortest_path(
    patches: list[Patch], edges: list[CorridorEdge], source_id: str, target_id: str
) -> ShortestPathResult | None:
    graph = build_graph(patches, edges)
    if source_id not in graph or target_id not in graph:
        return None
    try:
        path = nx.shortest_path(graph, source_id, target_id, weight="weight")
        cost = nx.shortest_path_length(graph, source_id, target_id, weight="weight")
    except nx.NetworkXNoPath:
        return None
    return ShortestPathResult(patch_ids=path, total_cost=cost)


def _split_large_geom(geom, name: str) -> list[tuple[float, str, float, float, object]]:
    """Splits a habitat polygon far bigger than one clamped patch circle into a
    regular grid of sub-pieces, so a whole park doesn't collapse into a single
    unrealistic circle at one arbitrary point."""
    minx, miny, maxx, maxy = geom.bounds
    pieces = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            piece = geom.intersection(box(x, y, x + SPLIT_CELL_M, y + SPLIT_CELL_M))
            if not piece.is_empty and piece.geom_type in ("Polygon", "MultiPolygon") and piece.area >= MIN_HABITAT_AREA_M2:
                centroid = piece.centroid
                pieces.append((piece.area, name, centroid.x, centroid.y, piece))
            y += SPLIT_CELL_M
        x += SPLIT_CELL_M
    return pieces


def _select_spread(pieces: list[tuple[float, str, float, float, object]], cap: int) -> list[tuple[float, str, float, float, object]]:
    """Picks `cap` pieces favoring both size and spatial spread: starts from
    the largest, then greedily adds whichever remaining piece is farthest
    from everything already picked. Plain top-N-by-area would pick this
    instead — most interior grid cells from _split_large_geom tie on area
    (uncropped forest, all ~SPLIT_CELL_M²), so a pure area sort just returns
    them in grid-scan order, i.e. one clustered column instead of patches
    spread across the polygon."""
    if len(pieces) <= cap:
        return pieces
    remaining = sorted(pieces, key=lambda c: c[0], reverse=True)
    selected = [remaining.pop(0)]
    while len(selected) < cap and remaining:
        best_idx, best_dist = 0, -1.0
        for i, candidate in enumerate(remaining):
            dist = min(math.hypot(candidate[2] - s[2], candidate[3] - s[3]) for s in selected)
            if dist > best_dist:
                best_dist, best_idx = dist, i
        selected.append(remaining.pop(best_idx))
    return selected


def generate_study_area(
    polygon: list[LatLngPoint], count: int
) -> tuple[list[Patch], dict[str, str], dict[str, object]]:
    """Returns the study area's patches, a patch-id -> source-polygon-id map
    (patches split from the same oversized source polygon, see
    _split_large_geom, share a source id, so build_corridors can always
    connect them to each other regardless of distance — they're pieces of one
    contiguous habitat block, not separate fragments needing dispersal), and a
    patch-id -> real habitat geometry map (EPSG:3857): a patch's `radius` is
    only a circle approximation for display/dispersal math, sized from the
    habitat's area — for a large or elongated polygon that circle can extend
    well past where the real habitat actually is, so anything checking overlap
    with a specific geometry (e.g. analyze_impact's footprint intersection)
    must use this real shape instead of `Point(lat, lng).buffer(radius)`."""
    ring = [(p.lng, p.lat) for p in polygon]
    polygon_4326 = gpd.GeoSeries([Polygon(ring)], crs="EPSG:4326").buffer(0)
    polygon_3857 = polygon_4326.to_crs(epsg=3857).iloc[0]

    bbox_wgs84 = terrain.bbox_3857_to_wgs84(polygon_3857.bounds)
    habitats = terrain.fetch_habitat_polygons(bbox_wgs84)

    # Cap how many sub-patches a single source polygon can contribute, so one
    # huge contiguous habitat block (common with WorldCover) can't crowd out
    # every smaller, genuinely distinct fragment elsewhere in the ranking.
    max_pieces_per_source = max(2, count // 2)

    candidates = []
    for source_idx, (name, geom) in enumerate(zip(habitats["name"], habitats.geometry)):
        source_id = f"s{source_idx}"
        # Habitat polygons are often much larger than the study window (e.g. a
        # forest bordering a road footprint) — clip to the window and measure
        # the clipped portion instead of testing the whole polygon's centroid,
        # or a patch that genuinely overlaps the window gets missed whenever
        # its overall centroid happens to fall outside it.
        clipped = geom.intersection(polygon_3857)
        if clipped.is_empty or clipped.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        area = clipped.area
        if area < MIN_HABITAT_AREA_M2:
            continue
        if area > MAX_PATCH_AREA_M2:
            pieces = _split_large_geom(clipped, name)
            for piece in _select_spread(pieces, max_pieces_per_source):
                candidates.append((*piece, source_id))
        else:
            centroid = clipped.centroid
            candidates.append((area, name, centroid.x, centroid.y, clipped, source_id))

    candidates.sort(key=lambda c: c[0], reverse=True)
    candidates = candidates[:count]

    patches = []
    source_groups: dict[str, str] = {}
    patch_geometries: dict[str, object] = {}
    for i, (area, name, x, y, geom, source_id) in enumerate(candidates):
        lat, lng = terrain.to_wgs84(x, y)
        radius = min(max(math.sqrt(area / math.pi), MIN_PATCH_RADIUS_M), MAX_PATCH_RADIUS_M)
        patch_name = name if isinstance(name, str) and name.strip() else f"Zona verde {i + 1}"
        patch_id = f"p{i}"
        patches.append(Patch(id=patch_id, name=patch_name, lat=lat, lng=lng, radius=radius))
        source_groups[patch_id] = source_id
        patch_geometries[patch_id] = geom
    return patches, source_groups, patch_geometries


def _buffer_polygon_wgs84(polygon: list[LatLngPoint], margin_m: float) -> list[LatLngPoint]:
    """Buffers a polygon (given in lat/lng) outward by margin_m meters, returning
    the analysis window used to search for surrounding habitat patches — mirrors
    the margin logic build_corridors already applies around a set of patches."""
    ring = [(p.lng, p.lat) for p in polygon]
    polygon_3857 = gpd.GeoSeries([Polygon(ring)], crs="EPSG:4326").buffer(0).to_crs(epsg=3857).iloc[0]
    buffered_4326 = gpd.GeoSeries([polygon_3857.buffer(margin_m)], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]
    return [LatLngPoint(lat=lat, lng=lng) for lng, lat in buffered_4326.exterior.coords]


def _footprint_to_3857(footprint: list[LatLngPoint]):
    ring = [(p.lng, p.lat) for p in footprint]
    return gpd.GeoSeries([Polygon(ring)], crs="EPSG:4326").buffer(0).to_crs(epsg=3857).iloc[0]


def _diff_corridors(
    baseline_edges: list[CorridorEdge],
    scenario_edges: list[CorridorEdge],
    lost_patch_ids: set[str],
) -> tuple[list[CorridorEdge], int]:
    scenario_keys = {_edge_key(e.source, e.target) for e in scenario_edges}
    lost: list[CorridorEdge] = []
    unaffected = 0
    for e in baseline_edges:
        if e.source in lost_patch_ids or e.target in lost_patch_ids:
            lost.append(e)
            continue
        if _edge_key(e.source, e.target) not in scenario_keys:
            lost.append(e)
            continue
        unaffected += 1
    return lost, unaffected


def analyze_impact(
    footprint: list[LatLngPoint],
    dispersal_distance: float,
    count: int,
) -> ImpactAnalysisResult:
    """Compares ecological connectivity before vs. after a proposed development
    footprint: patches the footprint overlaps are treated as destroyed, and the
    footprint itself is burned into the resistance grid as a barrier, so any
    surviving corridor that must detour around it becomes visibly costlier."""
    margin = max(dispersal_distance, 200.0)
    window_polygon = _buffer_polygon_wgs84(footprint, margin)
    baseline_patches, source_groups, patch_geometries = generate_study_area(window_polygon, count)

    footprint_3857 = _footprint_to_3857(footprint)
    patches_3857 = patches_to_geoframe(baseline_patches)
    # Uses each patch's real habitat geometry, not its display circle (patch.radius
    # is a circle approximation sized from area — for a large/elongated polygon
    # that circle can extend well past where the habitat actually is, which would
    # otherwise mark a patch "destroyed" by a footprint it never really touches).
    lost_ids = {
        p.id
        for p in baseline_patches
        if p.id in patch_geometries and patch_geometries[p.id].intersects(footprint_3857)
    }

    patches_lost = [p for p in baseline_patches if p.id in lost_ids]
    scenario_patches = [p for p in baseline_patches if p.id not in lost_ids]

    # Computed once from the full baseline patch set (scenario_patches is
    # always a subset of it) and passed to both calls below, so the scenario
    # call reuses baseline's already-cached OSM/WorldCover fetch instead of
    # re-querying Overpass for a near-identical area — see build_corridors.
    land_cover_bbox_3857 = None
    if len(baseline_patches) >= 2:
        bminx, bminy, bmaxx, bmaxy = patches_3857.total_bounds
        land_cover_bbox_3857 = (bminx - margin, bminy - margin, bmaxx + margin, bmaxy + margin)

    hidden_edge_keys = _same_source_edge_keys(source_groups)

    baseline_edges = build_corridors(
        baseline_patches, dispersal_distance, source_groups=source_groups, land_cover_bbox_3857=land_cover_bbox_3857
    )
    baseline_annotated, baseline_metrics = analyze_graph(baseline_patches, baseline_edges, hidden_edge_keys)

    scenario_edges = build_corridors(
        scenario_patches,
        dispersal_distance,
        footprint_3857=footprint_3857,
        footprint_resistance=terrain.FOOTPRINT_RESISTANCE,
        source_groups=source_groups,
        land_cover_bbox_3857=land_cover_bbox_3857,
    )
    scenario_annotated, scenario_metrics = analyze_graph(scenario_patches, scenario_edges, hidden_edge_keys)

    corridors_lost, unaffected_count = _diff_corridors(baseline_annotated, scenario_annotated, lost_ids)
    newly_isolated = sorted(
        (set(scenario_metrics.isolated_patch_ids) - lost_ids) - set(baseline_metrics.isolated_patch_ids)
    )

    return ImpactAnalysisResult(
        footprint=footprint,
        dispersal_distance=dispersal_distance,
        patches=baseline_patches,
        patches_lost=patches_lost,
        baseline=GraphResponse(edges=baseline_annotated, metrics=baseline_metrics),
        scenario=GraphResponse(edges=scenario_annotated, metrics=scenario_metrics),
        corridors_lost=corridors_lost,
        corridors_unaffected_count=unaffected_count,
        newly_isolated_patch_ids=newly_isolated,
        fragmentation_delta=scenario_metrics.fragmentation_index - baseline_metrics.fragmentation_index,
    )
