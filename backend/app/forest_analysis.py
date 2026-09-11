"""Core GeoAI engine: forest-loss and NDVI analysis for a single parcel.

Deforestation detection uses the Hansen Global Forest Change dataset
(UMD/hansen/global_forest_change_2025_v1_13) as the primary classification
source — it is an annually-updated, independently validated global forest
loss product, which gives the compliance verdict a defensible basis rather
than an in-house classifier. Sentinel-2 NDVI quarterly composites are pulled
alongside it to give visibility into the months not yet covered by the
latest Hansen update (which typically lags ~9-12 months).
"""

from datetime import date

import ee

from app.gee import get_ee_client

HANSEN_ASSET = "UMD/hansen/global_forest_change_2025_v1_13"
HANSEN_LATEST_LOSS_YEAR = 2025  # last year covered by the asset above (verified against lossyear band)
MIN_CONCLUSIVE_LOSS_AREA_HA = 0.1  # filters pixel-edge noise on tiny parcels

S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
NDVI_SCALE_M = 10
HANSEN_SCALE_M = 30


def _to_ee_geometry(geojson: dict) -> ee.Geometry:
    return ee.Geometry(geojson)


def _mask_s2_clouds(img: ee.Image) -> ee.Image:
    qa = img.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))
    return img.updateMask(mask).divide(10000).copyProperties(img, ["system:time_start"])


def _quarter_starts(start: date, end: date) -> list[date]:
    quarters = []
    year, month = start.year, ((start.month - 1) // 3) * 3 + 1
    cursor = date(year, month, 1)
    while cursor <= end:
        quarters.append(cursor)
        month = cursor.month + 3
        year = cursor.year + (1 if month > 12 else 0)
        month = month - 12 if month > 12 else month
        cursor = date(year, month, 1)
    return quarters


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def analyze_forest_loss(geometry: ee.Geometry, cutoff_date: date, min_tree_cover_pct: int) -> dict:
    hansen = ee.Image(HANSEN_ASSET)
    treecover2000 = hansen.select("treecover2000")
    loss = hansen.select("loss")
    lossyear = hansen.select("lossyear")  # 0 = no loss, N = loss in year 2000+N

    forest_baseline = treecover2000.gt(min_tree_cover_pct)
    cutoff_year_code = cutoff_date.year - 2000

    loss_after_cutoff = loss.eq(1).And(lossyear.gt(cutoff_year_code)).And(forest_baseline)
    loss_any_year = loss.eq(1).And(forest_baseline)

    pixel_area_ha = ee.Image.pixelArea().divide(10000)

    total_area = pixel_area_ha.reduceRegion(
        reducer=ee.Reducer.sum(), geometry=geometry, scale=HANSEN_SCALE_M,
        maxPixels=1e9, bestEffort=True,
    )
    baseline_forest_area = pixel_area_ha.updateMask(forest_baseline).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=geometry, scale=HANSEN_SCALE_M,
        maxPixels=1e9, bestEffort=True,
    )
    loss_after_cutoff_area = pixel_area_ha.updateMask(loss_after_cutoff).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=geometry, scale=HANSEN_SCALE_M,
        maxPixels=1e9, bestEffort=True,
    )
    year_breakdown = pixel_area_ha.addBands(lossyear.updateMask(loss_any_year)).reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1, groupName="year_code"),
        geometry=geometry, scale=HANSEN_SCALE_M, maxPixels=1e9, bestEffort=True,
    )

    combined = ee.Dictionary(
        {
            "total_area_ha": total_area.get("area"),
            "baseline_forest_area_ha": baseline_forest_area.get("area"),
            "loss_after_cutoff_area_ha": loss_after_cutoff_area.get("area"),
            "year_groups": year_breakdown.get("groups"),
        }
    )
    return combined.getInfo()


def get_quarterly_ndvi_series(geometry: ee.Geometry, start: date, end: date) -> list[dict]:
    s2 = (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(geometry)
        .filterDate(str(start), str(end))
        .map(_mask_s2_clouds)
    )

    quarter_specs = [
        {"start": str(q_start), "end": str(_add_months(q_start, 3))}
        for q_start in _quarter_starts(start, end)
    ]

    def quarter_feature(spec):
        spec = ee.Dictionary(spec)
        q_start = ee.Date(spec.get("start"))
        q_end = ee.Date(spec.get("end"))
        composite = s2.filterDate(q_start, q_end).median()
        ndvi = composite.normalizedDifference(["B8", "B4"]).rename("ndvi")
        stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=geometry, scale=NDVI_SCALE_M,
            maxPixels=1e9, bestEffort=True,
        )
        return ee.Feature(None, {"period_start": spec.get("start"), "ndvi_mean": stats.get("ndvi")})

    fc = ee.FeatureCollection(ee.List(quarter_specs).map(quarter_feature))
    features = fc.getInfo()["features"]
    return [f["properties"] for f in features]


def analyze_parcel(geojson: dict, cutoff_date: date, min_tree_cover_pct: int) -> dict:
    get_ee_client()
    geometry = _to_ee_geometry(geojson)

    forest = analyze_forest_loss(geometry, cutoff_date, min_tree_cover_pct)
    ndvi_series = get_quarterly_ndvi_series(geometry, date(2020, 1, 1), date.today())

    total_area_ha = forest.get("total_area_ha") or 0.0
    baseline_forest_area_ha = forest.get("baseline_forest_area_ha") or 0.0
    loss_after_cutoff_area_ha = forest.get("loss_after_cutoff_area_ha") or 0.0
    year_groups = forest.get("year_groups") or []

    yearly_loss = sorted(
        (
            {"year": 2000 + int(g["year_code"]), "area_ha": round(g["sum"], 4)}
            for g in year_groups
            if g.get("year_code") is not None and int(g["year_code"]) > 0
        ),
        key=lambda x: x["year"],
    )

    deforestation_detected = loss_after_cutoff_area_ha >= MIN_CONCLUSIVE_LOSS_AREA_HA
    compliance_status = "non_compliant" if deforestation_detected else "compliant"

    notes = [
        f"Baseline classification: Hansen Global Forest Change {HANSEN_ASSET.split('/')[-1]}, "
        f"last full year covered: {HANSEN_LATEST_LOSS_YEAR}.",
        "Sentinel-2 NDVI series covers months after the latest Hansen update for visual "
        "corroboration; it is not an independent loss-year classification.",
    ]
    if cutoff_date.year > HANSEN_LATEST_LOSS_YEAR:
        notes.append(
            f"Cutoff year {cutoff_date.year} is beyond the Hansen dataset's coverage "
            f"({HANSEN_LATEST_LOSS_YEAR}); recent months rely on the NDVI series only "
            "and the result should be treated as needs_review until a newer Hansen release "
            "or a dedicated recent-change model is available."
        )

    if cutoff_date.year > HANSEN_LATEST_LOSS_YEAR and not deforestation_detected:
        compliance_status = "needs_review"

    return {
        "parcel_area_ha": round(total_area_ha, 4),
        "baseline_forest_area_ha": round(baseline_forest_area_ha, 4),
        "loss_after_cutoff_area_ha": round(loss_after_cutoff_area_ha, 4),
        "deforestation_detected": deforestation_detected,
        "compliance_status": compliance_status,
        "yearly_loss_since_2001": yearly_loss,
        "ndvi_quarterly_series": ndvi_series,
        "dataset_notes": notes,
    }
