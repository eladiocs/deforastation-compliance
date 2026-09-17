export interface GeoJsonPolygonGeometry {
  type: 'Polygon' | 'MultiPolygon'
  coordinates: number[][][] | number[][][][]
}

/** Pulls a Polygon/MultiPolygon geometry out of a bare geometry, a GeoJSON
 * Feature, or a FeatureCollection (merging multiple polygons into a
 * MultiPolygon), or returns null if none is found. */
export function extractPolygonGeometry(parsed: any): GeoJsonPolygonGeometry | null {
  if (parsed?.type === 'FeatureCollection') {
    const geometries = (parsed.features ?? [])
      .map((feature: any) => feature.geometry)
      .filter((geometry: any) => geometry?.type === 'Polygon' || geometry?.type === 'MultiPolygon')
    if (geometries.length === 0) return null
    if (geometries.length === 1) return geometries[0]
    return {
      type: 'MultiPolygon',
      coordinates: geometries.flatMap((geometry: any) =>
        geometry.type === 'MultiPolygon' ? geometry.coordinates : [geometry.coordinates],
      ),
    }
  }
  const geometry = parsed?.type === 'Feature' ? parsed.geometry : parsed
  if (geometry?.type !== 'Polygon' && geometry?.type !== 'MultiPolygon') return null
  return geometry
}

function ringArea(ring: number[][]): number {
  // Shoelace formula on raw lng/lat — only used to compare ring sizes, not for a real metric area.
  let sum = 0
  for (let i = 0; i < ring.length; i++) {
    const [x1, y1] = ring[i]
    const [x2, y2] = ring[(i + 1) % ring.length]
    sum += x1 * y2 - x2 * y1
  }
  return Math.abs(sum / 2)
}

/** The backend's footprint contract is a single ring — collapse a MultiPolygon
 * upload to its largest polygon's outer ring (a deliberate v1 simplification). */
export function largestRing(geometry: GeoJsonPolygonGeometry): { lat: number; lng: number }[] {
  const outerRings: number[][][] =
    geometry.type === 'MultiPolygon'
      ? (geometry.coordinates as number[][][][]).map((polygon) => polygon[0])
      : [(geometry.coordinates as number[][][])[0]]

  const largest = outerRings.reduce((a, b) => (ringArea(a) >= ringArea(b) ? a : b))
  return largest.map(([lng, lat]) => ({ lat, lng }))
}
