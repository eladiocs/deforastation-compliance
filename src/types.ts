export interface Patch {
  id: string
  name: string
  lat: number
  lng: number
  radius: number
}

export interface CorridorEdge {
  source: string
  target: string
  distance: number
  resistance: number
  cost: number
  betweenness: number
  route: { lat: number; lng: number }[]
}

export interface TopCorridor {
  edge: CorridorEdge
  betweenness: number
}

export interface GraphMetrics {
  totalPatches: number
  totalCorridors: number
  componentCount: number
  isolatedPatchIds: string[]
  largestComponentSize: number
  fragmentationIndex: number
  topCorridors: TopCorridor[]
}

export interface ShortestPathResult {
  patchIds: string[]
  totalCost: number
}

export interface Parcel {
  id: number
  name: string
  footprint: { lat: number; lng: number }[]
  createdAt: string
}

export interface AnalysisCreateRequest {
  dispersalDistance: number
  dispersalLabel: string
  count: number
  projectMeta: { description: string; preparedBy: string }
}

export interface Analysis {
  id: number
  parcelId: number
  dispersalDistance: number
  dispersalLabel: string
  count: number
  projectMeta: { description: string; preparedBy: string }
  result: ImpactAnalysisResult
  createdAt: string
}

export interface ImpactAnalysisResult {
  footprint: { lat: number; lng: number }[]
  dispersalDistance: number
  patches: Patch[]
  patchesLost: Patch[]
  baseline: { edges: CorridorEdge[]; metrics: GraphMetrics }
  scenario: { edges: CorridorEdge[]; metrics: GraphMetrics }
  corridorsLost: CorridorEdge[]
  corridorsUnaffectedCount: number
  newlyIsolatedPatchIds: string[]
  fragmentationDelta: number
}
