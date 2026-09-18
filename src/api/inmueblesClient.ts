import axios from 'axios'

import type { Analysis, GeoJsonPoint, Parcel } from './inmueblesTypes'

const apiUrl = import.meta.env.VITE_API_URL_INMUEBLES ?? 'http://localhost:8200'

const http = axios.create({ baseURL: apiUrl })

export interface CreateParcelPayload {
  name: string
  address?: string | null
  geometry: GeoJsonPoint
}

export interface UpdateParcelPayload {
  name: string
  address?: string | null
}

export interface CreateAnalysisPayload {
  buffer_radius_m?: number
}

export const api = {
  listParcels: () => http.get<Parcel[]>('/parcels').then((r) => r.data),
  getParcel: (id: number | string) => http.get<Parcel>(`/parcels/${id}`).then((r) => r.data),
  createParcel: (payload: CreateParcelPayload) => http.post<Parcel>('/parcels', payload).then((r) => r.data),
  updateParcel: (id: number | string, payload: UpdateParcelPayload) =>
    http.patch<Parcel>(`/parcels/${id}`, payload).then((r) => r.data),
  deleteParcel: (id: number | string) => http.delete(`/parcels/${id}`).then(() => undefined),
  listParcelAnalyses: (parcelId: number | string) =>
    http.get<Analysis[]>(`/parcels/${parcelId}/analyses`).then((r) => r.data),
  createAnalysis: (parcelId: number | string, payload: CreateAnalysisPayload) =>
    http.post<Analysis>(`/parcels/${parcelId}/analyses`, payload).then((r) => r.data),
  getAnalysis: (id: number | string) => http.get<Analysis>(`/analyses/${id}`).then((r) => r.data),
  deleteAnalysis: (id: number | string) => http.delete(`/analyses/${id}`).then(() => undefined),
  reportUrl: (analysisId: number | string) => `${apiUrl}/analyses/${analysisId}/report`,
}

export function checkHealth(): Promise<boolean> {
  return http
    .get('/health', { timeout: 5_000 })
    .then(() => true)
    .catch(() => false)
}
