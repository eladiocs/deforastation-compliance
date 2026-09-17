import L from 'leaflet'

export function createStreetLayer(): L.TileLayer {
  return L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap',
    maxZoom: 19,
  })
}

export function createSatelliteLayer(): L.TileLayer {
  return L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    {
      attribution: 'Tiles &copy; Esri',
      maxZoom: 19,
    },
  )
}

/** Añade el switcher de capas (calles/satélite) y devuelve la capa satélite, ya añadida al mapa por defecto. */
export function addBaseLayers(map: L.Map): L.TileLayer {
  const streetLayer = createStreetLayer()
  const satelliteLayer = createSatelliteLayer().addTo(map)
  L.control.layers({ Calles: streetLayer, Satélite: satelliteLayer }).addTo(map)
  return satelliteLayer
}

export interface GeocodedCity {
  lat: number
  lon: number
}

/** Geocodifica un nombre de ciudad/lugar vía Nominatim (OpenStreetMap). */
export async function geocodeCity(query: string): Promise<GeocodedCity | null> {
  const response = await fetch(
    `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`,
  )
  if (!response.ok) throw new Error('Nominatim request failed')
  const results: Array<{ lat: string; lon: string }> = await response.json()
  const result = results[0]
  return result ? { lat: Number(result.lat), lon: Number(result.lon) } : null
}
