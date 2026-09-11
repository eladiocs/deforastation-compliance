export interface GeoJsonPolygon {
  type: 'Polygon' | 'MultiPolygon'
  coordinates: unknown[]
}

export interface Parcel {
  id: string
  name: string
  client_name: string | null
  commodity: string | null
  geometry: GeoJsonPolygon
  created_at: string
}

export interface YearlyLoss {
  year: number
  area_ha: number
}

export interface NdviPoint {
  period_start: string
  ndvi_mean: number | null
}

export type ComplianceStatus = 'compliant' | 'non_compliant' | 'needs_review'

export interface Analysis {
  id: string
  parcel_id: string
  cutoff_date: string
  min_tree_cover_pct: number
  parcel_area_ha: number
  baseline_forest_area_ha: number
  loss_after_cutoff_area_ha: number
  deforestation_detected: boolean
  compliance_status: ComplianceStatus
  yearly_loss_since_2001: YearlyLoss[]
  ndvi_quarterly_series: NdviPoint[]
  dataset_notes: string[]
  report_sha256: string | null
  created_at: string
}
