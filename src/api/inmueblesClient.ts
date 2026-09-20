import type { Analysis, GeoJsonPoint, Parcel } from './inmueblesTypes'

const apiUrl = import.meta.env.VITE_API_URL_INMUEBLES ?? 'http://localhost:8200'

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
  address?: string | null
  geometry: GeoJsonPoint
}

export interface UpdateParcelPayload {
  name: string
  address?: string | null
}

export const api = {
  listParcels: () => getJSON<Parcel[]>('/parcels'),
  getParcel: (id: number | string) => getJSON<Parcel>(`/parcels/${id}`),
  createParcel: (payload: CreateParcelPayload) => sendJSON<Parcel>('/parcels', 'POST', payload),
  updateParcel: (id: number | string, payload: UpdateParcelPayload) =>
    sendJSON<Parcel>(`/parcels/${id}`, 'PATCH', payload),
  deleteParcel: (id: number | string) => deleteRequest(`/parcels/${id}`),
  listParcelAnalyses: (parcelId: number | string) => getJSON<Analysis[]>(`/parcels/${parcelId}/analyses`),
  createAnalysis: (parcelId: number | string) => sendJSON<Analysis>(`/parcels/${parcelId}/analyses`, 'POST', {}),
  getAnalysis: (id: number | string) => getJSON<Analysis>(`/analyses/${id}`),
  deleteAnalysis: (id: number | string) => deleteRequest(`/analyses/${id}`),
  reportUrl: (analysisId: number | string) => `${apiUrl}/analyses/${analysisId}/report`,
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
