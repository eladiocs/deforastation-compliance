"""Core GeoAI engine: flood-risk scoring for a single point (property location).

Uses two independently-produced, defensible global datasets rather than an
in-house classifier — Copernicus DEM GLO-30 (elevation/slope) and the JRC
Global Surface Water dataset (historical water occurrence, 1984-2021) — the
same "cite a real dataset, not a black box" approach as the anti-deforestación
module's use of Hansen Global Forest Change. The combined score is a
documented rule-based function of both; see `_score_and_label` for the exact
thresholds.

This is a support tool, not a hydraulic model, and the result does not
replace official flood-zone layers (e.g. SNCZI in Spain) for regulatory use.
Every input is evaluated at the point itself — the subject is always a single
construction/dwelling, not an area, so there is no buffer/analysis-radius
parameter anywhere in this module.

Elevation risk and the channel/permanent-water proximity signals are all
checked against MERIT Hydro's own `hnd` band (its native, precomputed Height
Above Nearest Drainage, "HAND") to discard false positives on terrain that is
horizontally close to water but sits well above it — e.g. Teruel's old town,
built on a promontory ~50 m above the Turia/Alfambra valley, or the Alcázar
de Toledo on its promontory above the Tajo gorge: `distance_to_channel_m`/
`distance_to_water_m` alone found water nearby (an artifact of how distance
is aggregated over a wide search radius, not of real proximity) and scored
"alto"/"medio" despite the point being nowhere near reachable by that
water's flooding.
"""

import ee

from app.gee import get_ee_client

DEM_ASSET = "COPERNICUS/DEM/GLO30"
DEM_BAND = "DEM"
DEM_SCALE_M = 30

GSW_ASSET = "JRC/GSW1_4/GlobalSurfaceWater"
GSW_SCALE_M = 30
PERMANENT_WATER_OCCURRENCE_PCT = 50.0
WATER_SEARCH_RADIUS_M = 1000.0

# JRC Global Surface Water only sees water that was visibly wet in optical
# satellite imagery — it misses ephemeral Mediterranean ravines ("barrancos"/
# "ramblas") that are dry most of the year and only carry water during flash
# floods (exactly the mechanism behind the 2024 Valencia DANA). MERIT Hydro's
# upstream drainage area is derived from terrain, not observed water, so it
# flags these dry channels too.
MERIT_ASSET = "MERIT/Hydro/v1_0_1"
MERIT_SCALE_M = 90
# A low threshold (e.g. 1 km², the usual default for extracting a dense
# stream network from flow accumulation) also flags minor hillside rills near
# any high point — verified empirically: a control point deep in the Sierra
# Calderona, nowhere near a real watercourse, still had ~4 km² of upstream
# area within 1 km. The Barranco del Poyo at Paiporta (the channel behind the
# October 2024 Valencia flood) has ~413 km². 10 km² separates "a channel that
# can carry a dangerous flash flood" from ordinary hillside drainage.
CHANNEL_MIN_UPSTREAM_AREA_KM2 = 10.0

POINT_SAMPLE_RADIUS_M = 15.0  # smooths out a single noisy DEM/GSW pixel at the point

# MERIT Hydro's own "hnd" band (Height Above Nearest Drainage), natively
# co-registered with "upa" — no cross-dataset reprojection needed, unlike an
# earlier attempt at this that mixed the 30 m Copernicus DEM with MERIT's
# ~90 m grid and produced unreliable None results. Empirically, real
# flood-risk sites (Almoradí, Biescas, Sant Llorenç, DANA Valencia, Mocoa,
# Galacho de Juslibol) all measured under 12 m; known-safe elevated sites
# (Teruel's old town, a control point in Extremadura) measured over 40 m —
# a wide, clean gap, so 20 m is a safe cutoff with margin on both sides.
#
# HAND — not a buffer-relative elevation proxy — is also the basis for the
# elevation risk factor itself: it is a real, point-evaluated hydrological
# measurement (height above the nearest drainage network) and needs no
# analysis radius, unlike the old "height above the lowest point within an
# arbitrary buffer" approximation it replaced.
HAND_HIGH_RISK_M = 12.0
CHANNEL_SAFE_HAND_M = 20.0


def _point_buffer(point: ee.Geometry, radius_m: float) -> ee.Geometry:
    return point.buffer(radius_m)


def _reduce_scalar(image: ee.Image, geometry: ee.Geometry, reducer: ee.Reducer, scale: int) -> float | None:
    stats = image.reduceRegion(reducer=reducer, geometry=geometry, scale=scale, maxPixels=1e9, bestEffort=True)
    value = stats.getInfo()
    return next(iter(value.values()), None)


def _distance_to_permanent_water_m(point: ee.Geometry) -> float:
    """Approximate distance (m) from the point to the nearest pixel classified
    as permanently occupied by water. fastDistanceTransform returns squared
    pixel-count distance; sqrt() converts to pixel count, and multiplying by
    the source resolution gives an approximate metric distance — adequate for
    a risk-tier signal, not survey-grade.

    Evaluated at the point itself (small sample radius), not reduced with
    min() over the wide search buffer: min() over a 1000 m buffer picks up
    any water body's own near-zero self-distance if it merely passes within
    that buffer, which reports ~0 m even when the point itself is hundreds of
    metres away (found on the Alcázar de Toledo, real distance 706 m,
    buffer-min reported 0 m). fastDistanceTransform's neighborhood (256 px)
    already searches far beyond the old buffer radius, so shrinking the
    reduceRegion geometry doesn't reduce how far the transform can find water."""
    sample_area = _point_buffer(point, POINT_SAMPLE_RADIUS_M)
    gsw_occurrence = ee.Image(GSW_ASSET).select("occurrence")
    permanent_water = gsw_occurrence.gte(PERMANENT_WATER_OCCURRENCE_PCT)

    distance_img = permanent_water.selfMask().fastDistanceTransform(256).sqrt().multiply(GSW_SCALE_M)
    value = _reduce_scalar(distance_img, sample_area, ee.Reducer.mean(), GSW_SCALE_M)
    return float(value) if value is not None else WATER_SEARCH_RADIUS_M


def _distance_to_drainage_channel_m(point: ee.Geometry) -> float:
    """Approximate distance (m) to the nearest terrain-defined drainage
    channel — flags dry ravines/barrancos that JRC's water-occurrence signal
    misses, since this comes from upstream drainage area (a terrain property),
    not from whether the channel was ever seen wet by satellite.

    Evaluated at the point itself, not reduced with min() over the wide
    search buffer — same reasoning as `_distance_to_permanent_water_m`."""
    sample_area = _point_buffer(point, POINT_SAMPLE_RADIUS_M)
    upstream_area = ee.Image(MERIT_ASSET).select("upa")
    channel = upstream_area.gte(CHANNEL_MIN_UPSTREAM_AREA_KM2)

    distance_img = channel.selfMask().fastDistanceTransform(256).sqrt().multiply(MERIT_SCALE_M)
    value = _reduce_scalar(distance_img, sample_area, ee.Reducer.mean(), MERIT_SCALE_M)
    return float(value) if value is not None else WATER_SEARCH_RADIUS_M


def _score_and_label(
    water_occurrence_pct: float,
    distance_to_water_m: float,
    distance_to_channel_m: float,
    slope_pct: float,
    hand_m: float,
) -> tuple[float, str, list[dict]]:
    """Weighted rule-based score, 0-100. Documented thresholds instead of a
    trained model — mirrors the compliance-status logic in the
    anti-deforestación module: a defensible, explainable basis over a black
    box the client can't interrogate."""

    factors: list[dict] = []

    if water_occurrence_pct >= 25:
        water_score, water_sev = 30.0, "alto"
    elif water_occurrence_pct >= 5:
        water_score, water_sev = 15.0, "medio"
    else:
        water_score, water_sev = 0.0, "bajo"
    factors.append(
        {
            "key": "water_occurrence",
            "label": "Ocupación histórica de agua en el punto (1984-2021)",
            "value": round(water_occurrence_pct, 1),
            "unit": "%",
            "severity": water_sev,
        }
    )

    if hand_m >= CHANNEL_SAFE_HAND_M:
        channel_score, channel_sev = 0.0, "bajo"
        channel_label = (
            "Distancia a un cauce de drenaje (incl. barrancos/ramblas secos) — "
            f"descartado: el punto está {hand_m:.0f} m por encima del drenaje "
            "más cercano (MERIT Hydro HAND)"
        )
    elif distance_to_channel_m < 100:
        channel_score, channel_sev = 30.0, "alto"
        channel_label = "Distancia a un cauce de drenaje (incl. barrancos/ramblas secos)"
    elif distance_to_channel_m < 300:
        channel_score, channel_sev = 15.0, "medio"
        channel_label = "Distancia a un cauce de drenaje (incl. barrancos/ramblas secos)"
    else:
        channel_score, channel_sev = 0.0, "bajo"
        channel_label = "Distancia a un cauce de drenaje (incl. barrancos/ramblas secos)"
    factors.append(
        {
            "key": "distance_to_channel",
            "label": channel_label,
            "value": round(distance_to_channel_m, 1),
            "unit": "m",
            "severity": channel_sev,
        }
    )

    if hand_m < HAND_HIGH_RISK_M:
        elev_score, elev_sev = 25.0, "alto"
    elif hand_m < CHANNEL_SAFE_HAND_M:
        elev_score, elev_sev = 12.0, "medio"
    else:
        elev_score, elev_sev = 0.0, "bajo"
    factors.append(
        {
            "key": "hand",
            "label": "Altura sobre el drenaje más cercano (HAND, MERIT Hydro)",
            "value": round(hand_m, 1),
            "unit": "m",
            "severity": elev_sev,
        }
    )

    if hand_m >= CHANNEL_SAFE_HAND_M:
        dist_score, dist_sev = 0.0, "bajo"
        dist_label = (
            "Distancia a agua permanente conocida — descartado: el punto "
            f"está {hand_m:.0f} m por encima del drenaje más cercano "
            "(MERIT Hydro HAND)"
        )
    elif distance_to_water_m < 50:
        dist_score, dist_sev = 10.0, "alto"
        dist_label = "Distancia a agua permanente conocida"
    elif distance_to_water_m < 200:
        dist_score, dist_sev = 5.0, "medio"
        dist_label = "Distancia a agua permanente conocida"
    else:
        dist_score, dist_sev = 0.0, "bajo"
        dist_label = "Distancia a agua permanente conocida"
    factors.append(
        {
            "key": "distance_to_water",
            "label": dist_label,
            "value": round(distance_to_water_m, 1),
            "unit": "m",
            "severity": dist_sev,
        }
    )

    if slope_pct < 2:
        slope_score, slope_sev = 5.0, "medio"
    else:
        slope_score, slope_sev = 0.0, "bajo"
    factors.append(
        {
            "key": "slope",
            "label": "Pendiente del terreno (capacidad de drenaje)",
            "value": round(slope_pct, 1),
            "unit": "%",
            "severity": slope_sev,
        }
    )

    score = min(100.0, water_score + channel_score + elev_score + dist_score + slope_score)

    if score >= 60:
        label = "muy_alto"
    elif score >= 35:
        label = "alto"
    elif score >= 15:
        label = "medio"
    else:
        label = "bajo"

    return score, label, factors


def analyze_point(lat: float, lng: float) -> dict:
    get_ee_client()

    point = ee.Geometry.Point([lng, lat])
    sample_area = _point_buffer(point, POINT_SAMPLE_RADIUS_M)

    dem = ee.ImageCollection(DEM_ASSET).select(DEM_BAND).mosaic()
    slope = ee.Terrain.slope(dem)
    gsw_occurrence = ee.Image(GSW_ASSET).select("occurrence").unmask(0)

    elevation_m = _reduce_scalar(dem, sample_area, ee.Reducer.mean(), DEM_SCALE_M)
    slope_pct = _reduce_scalar(slope, sample_area, ee.Reducer.mean(), DEM_SCALE_M) or 0.0
    water_occurrence_pct = _reduce_scalar(gsw_occurrence, sample_area, ee.Reducer.mean(), GSW_SCALE_M) or 0.0

    if elevation_m is None:
        raise ValueError("No hay datos de elevación disponibles para este punto")

    distance_to_water_m = _distance_to_permanent_water_m(point)
    distance_to_channel_m = _distance_to_drainage_channel_m(point)

    hand = ee.Image(MERIT_ASSET).select("hnd")
    hand_m = _reduce_scalar(hand, sample_area, ee.Reducer.mean(), MERIT_SCALE_M)
    if hand_m is None:
        raise ValueError("No hay datos HAND (MERIT Hydro) disponibles para este punto")

    risk_score, risk_label, risk_factors = _score_and_label(
        water_occurrence_pct,
        distance_to_water_m,
        distance_to_channel_m,
        slope_pct,
        hand_m,
    )

    notes = [
        "Elevación y pendiente: Copernicus DEM GLO-30 (resolución 30 m).",
        "Ocupación histórica de agua y distancia a agua permanente: JRC Global "
        "Surface Water v1.4 (1984-2021, resolución 30 m); 'agua permanente' se "
        "define como ocupación histórica >= 50%.",
        "Distancia a cauce de drenaje: MERIT Hydro (área de drenaje aguas "
        "arriba, resolución ~90 m); un 'cauce' es cualquier punto con >= "
        f"{CHANNEL_MIN_UPSTREAM_AREA_KM2} km² de cuenca aguas arriba. Se basa "
        "en el terreno, no en si históricamente se vio con agua — por eso "
        "detecta barrancos y ramblas secos que JRC Global Surface Water pasa "
        "por alto.",
        "Altura sobre el drenaje más cercano (HAND): banda 'hnd' de MERIT "
        "Hydro, medida directamente en el punto (no un promedio sobre un "
        "área). Es el factor que determina el riesgo por elevación y también "
        "descarta el riesgo por cercanía a un cauce o a agua permanente "
        f"cuando el punto está >= {CHANNEL_SAFE_HAND_M:.0f} m por encima del "
        "drenaje más cercano — para no penalizar ubicaciones claramente "
        "elevadas sobre un valle o cauce cercano en horizontal pero "
        "inalcanzable por su inundación (p. ej. un promontorio junto a un río "
        "encajonado).",
        "Este resultado es una herramienta de apoyo y complementa (sin sustituir) "
        "las capas oficiales de zonas inundables (p. ej. SNCZI en España), "
        "detectando cauces y barrancos que estas, al basarse solo en cursos de "
        "agua formalmente estudiados, pueden no tener mapeados. No reemplaza un "
        "estudio hidrológico-hidráulico formal ni dichas capas oficiales para "
        "trámites regulatorios.",
    ]

    return {
        "elevation_m": round(elevation_m, 2),
        "hand_m": round(hand_m, 2),
        "slope_pct": round(slope_pct, 2),
        "water_occurrence_pct": round(water_occurrence_pct, 2),
        "distance_to_water_m": round(distance_to_water_m, 2),
        "distance_to_channel_m": round(distance_to_channel_m, 2),
        "risk_score": round(risk_score, 1),
        "risk_label": risk_label,
        "risk_factors": risk_factors,
        "dataset_notes": notes,
    }
