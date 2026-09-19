import type { Analysis, GeoJsonPolygon, Parcel } from './types'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8010'

const REQUEST_TIMEOUT_MS = 120_000

async function timedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    return await fetch(`${apiUrl}${path}`, { ...init, signal: controller.signal })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('El análisis tardó demasiado y se canceló. Inténtalo de nuevo en unos minutos.')
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

async function handleResponse<T>(response: Response, path: string): Promise<T> {
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail ?? `Error ${response.status} al llamar a ${path}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function getJSON<T>(path: string): Promise<T> {
  return timedFetch(path).then((r) => handleResponse<T>(r, path))
}

function sendJSON<T>(path: string, method: string, body: unknown): Promise<T> {
  return timedFetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((r) => handleResponse<T>(r, path))
}

function deleteRequest(path: string): Promise<void> {
  return timedFetch(path, { method: 'DELETE' }).then((r) => handleResponse<void>(r, path))
}

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
  listParcels: () => getJSON<Parcel[]>('/api/v1/parcels'),
  getParcel: (id: string) => getJSON<Parcel>(`/api/v1/parcels/${id}`),
  createParcel: (payload: CreateParcelPayload) => sendJSON<Parcel>('/api/v1/parcels', 'POST', payload),
  updateParcel: (id: string, payload: UpdateParcelPayload) =>
    sendJSON<Parcel>(`/api/v1/parcels/${id}`, 'PATCH', payload),
  deleteParcel: (id: string) => deleteRequest(`/api/v1/parcels/${id}`),
  listParcelAnalyses: (parcelId: string) => getJSON<Analysis[]>(`/api/v1/parcels/${parcelId}/analyses`),
  createAnalysis: (parcelId: string, payload: CreateAnalysisPayload) =>
    sendJSON<Analysis>(`/api/v1/parcels/${parcelId}/analyses`, 'POST', payload),
  getAnalysis: (id: string) => getJSON<Analysis>(`/api/v1/analyses/${id}`),
  deleteAnalysis: (id: string) => deleteRequest(`/api/v1/analyses/${id}`),
  reportUrl: (analysisId: string) => `${apiUrl}/api/v1/analyses/${analysisId}/report`,
}

const HEALTH_CHECK_TIMEOUT_MS = 5_000

export function checkHealth(): Promise<boolean> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT_MS)
  return fetch(`${apiUrl}/health`, { signal: controller.signal })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => clearTimeout(timeoutId))
}
