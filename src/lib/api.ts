import type {
  Analysis,
  AnalysisCreateRequest,
  CorridorEdge,
  GraphMetrics,
  ImpactAnalysisResult,
  Parcel,
  Patch,
  ShortestPathResult,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL_CORREDORES ?? 'http://localhost:8100'

// No request — the impact analysis in particular, which can chain several
// live OSM/satellite lookups — should ever leave the UI "loading" indefinitely.
// Hard-cap every call client-side so a slow/unresponsive backend always
// surfaces a clear error within a bounded time instead of hanging forever.
const REQUEST_TIMEOUT_MS = 120_000

async function timedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    return await fetch(`${API_BASE_URL}${path}`, { ...init, signal: controller.signal })
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

async function getJSON<T>(path: string): Promise<T> {
  const response = await timedFetch(path)
  return handleResponse<T>(response, path)
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const response = await timedFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response, path)
}

async function patchJSON<T>(path: string, body: unknown): Promise<T> {
  const response = await timedFetch(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response, path)
}

async function deleteRequest(path: string): Promise<void> {
  const response = await timedFetch(path, { method: 'DELETE' })
  return handleResponse<void>(response, path)
}

const HEALTH_CHECK_TIMEOUT_MS = 5_000

export async function checkHealth(): Promise<boolean> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE_URL}/health`, { signal: controller.signal })
    return response.ok
  } catch {
    return false
  } finally {
    clearTimeout(timeoutId)
  }
}

export function generateStudyArea(
  polygon: { lat: number; lng: number }[],
  count: number,
): Promise<Patch[]> {
  return postJSON<Patch[]>('/study-area/generate', { polygon, count })
}

export function buildGraph(
  patches: Patch[],
  dispersalDistance: number,
): Promise<{ edges: CorridorEdge[]; metrics: GraphMetrics }> {
  return postJSON('/graph/build', { patches, dispersalDistance })
}

export function fetchShortestPath(
  patches: Patch[],
  dispersalDistance: number,
  sourceId: string,
  targetId: string,
): Promise<ShortestPathResult> {
  return postJSON('/graph/shortest-path', { patches, dispersalDistance, sourceId, targetId })
}

export function fetchImpactAnalysis(
  footprint: { lat: number; lng: number }[],
  dispersalDistance: number,
  count = 15,
): Promise<ImpactAnalysisResult> {
  return postJSON('/impact-analysis', { footprint, dispersalDistance, count })
}

export function createAnalysis(
  parcelId: number | string,
  request: AnalysisCreateRequest,
): Promise<Analysis> {
  return postJSON<Analysis>(`/parcels/${parcelId}/analyses`, request)
}

export function listAnalyses(parcelId: number | string): Promise<Analysis[]> {
  return getJSON<Analysis[]>(`/parcels/${parcelId}/analyses`)
}

export function analysisReportUrl(analysisId: number): string {
  return `${API_BASE_URL}/analyses/${analysisId}/report`
}

export function deleteAnalysis(analysisId: number): Promise<void> {
  return deleteRequest(`/analyses/${analysisId}`)
}

export function listParcels(): Promise<Parcel[]> {
  return getJSON<Parcel[]>('/parcels')
}

export function getParcel(id: number | string): Promise<Parcel> {
  return getJSON<Parcel>(`/parcels/${id}`)
}

export function createParcel(
  name: string,
  footprint: { lat: number; lng: number }[],
): Promise<Parcel> {
  return postJSON<Parcel>('/parcels', { name, footprint })
}

export function updateParcel(id: number | string, name: string): Promise<Parcel> {
  return patchJSON<Parcel>(`/parcels/${id}`, { name })
}

export function deleteParcel(id: number | string): Promise<void> {
  return deleteRequest(`/parcels/${id}`)
}
