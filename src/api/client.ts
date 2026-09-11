import axios from 'axios'

import type { Analysis, GeoJsonPolygon, Parcel } from './types'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8010'

const http = axios.create({ baseURL: apiUrl })

export interface CreateParcelPayload {
  name: string
  client_name?: string | null
  commodity?: string | null
  geometry: GeoJsonPolygon
}

export interface UpdateParcelPayload {
  name: string
  client_name?: string | null
  commodity?: string | null
}

export interface CreateAnalysisPayload {
  cutoff_date?: string
  min_tree_cover_pct?: number
}

export const api = {
  listParcels: () => http.get<Parcel[]>('/api/v1/parcels').then((r) => r.data),
  getParcel: (id: string) => http.get<Parcel>(`/api/v1/parcels/${id}`).then((r) => r.data),
  createParcel: (payload: CreateParcelPayload) =>
    http.post<Parcel>('/api/v1/parcels', payload).then((r) => r.data),
  updateParcel: (id: string, payload: UpdateParcelPayload) =>
    http.patch<Parcel>(`/api/v1/parcels/${id}`, payload).then((r) => r.data),
  deleteParcel: (id: string) => http.delete(`/api/v1/parcels/${id}`).then(() => undefined),
  listParcelAnalyses: (parcelId: string) =>
    http.get<Analysis[]>(`/api/v1/parcels/${parcelId}/analyses`).then((r) => r.data),
  createAnalysis: (parcelId: string, payload: CreateAnalysisPayload) =>
    http.post<Analysis>(`/api/v1/parcels/${parcelId}/analyses`, payload).then((r) => r.data),
  getAnalysis: (id: string) => http.get<Analysis>(`/api/v1/analyses/${id}`).then((r) => r.data),
  deleteAnalysis: (id: string) => http.delete(`/api/v1/analyses/${id}`).then(() => undefined),
  reportUrl: (analysisId: string) => `${apiUrl}/api/v1/analyses/${analysisId}/report`,
}
