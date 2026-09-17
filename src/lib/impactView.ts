import type { EdgeStatus } from '@/components/FootprintMap.vue'
import type { ImpactAnalysisResult } from '@/types'

export function edgeKey(a: string, b: string): string {
  return a < b ? `${a}|${b}` : `${b}|${a}`
}

export function buildEdgeStatusMap(result: ImpactAnalysisResult | null): Map<string, EdgeStatus> {
  const map = new Map<string, EdgeStatus>()
  if (!result) return map
  for (const e of result.corridorsLost) map.set(edgeKey(e.source, e.target), 'lost')
  return map
}

export function lostPatchIds(result: ImpactAnalysisResult | null): Set<string> {
  return new Set(result?.patchesLost.map((p) => p.id) ?? [])
}

export function isolatedPatchIds(result: ImpactAnalysisResult | null): Set<string> {
  return new Set(result?.newlyIsolatedPatchIds ?? [])
}
