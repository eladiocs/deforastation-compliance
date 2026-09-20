export interface GeoJsonPoint {
  type: 'Point'
  coordinates: [number, number]
}

export interface Parcel {
  id: number
  name: string
  address: string | null
  geometry: GeoJsonPoint
  created_at: string
}

export type RiskSeverity = 'bajo' | 'medio' | 'alto'
export type RiskLabel = 'bajo' | 'medio' | 'alto' | 'muy_alto'

export interface RiskFactor {
  key: string
  label: string
  value: number
  unit: string
  severity: RiskSeverity
}

export interface Analysis {
  id: number
  parcel_id: number
  elevation_m: number
  hand_m: number
  slope_pct: number
  water_occurrence_pct: number
  distance_to_water_m: number
  distance_to_channel_m: number
  risk_score: number
  risk_label: RiskLabel
  risk_factors: RiskFactor[]
  dataset_notes: string[]
  created_at: string
}
