import { computed, reactive, ref } from 'vue'
import * as api from '@/lib/api'
import { DISPERSAL_PRESETS } from '@/lib/dispersalPresets'
import type { Analysis } from '@/types'

export interface ProjectMeta {
  description: string
  preparedBy: string
}

const DEFAULT_DISPERSAL_PRESET_ID = DISPERSAL_PRESETS[1].id
const DEFAULT_CUSTOM_DISPERSAL_DISTANCE = 300

export function useImpactAnalysis() {
  const footprint = ref<{ lat: number; lng: number }[]>([])

  const dispersalPresetId = ref(DEFAULT_DISPERSAL_PRESET_ID) // micromamíferos, a reasonable default
  const customDispersalDistance = ref(DEFAULT_CUSTOM_DISPERSAL_DISTANCE)
  const dispersalDistance = computed(() => {
    const preset = DISPERSAL_PRESETS.find((p) => p.id === dispersalPresetId.value)
    return preset?.distance ?? customDispersalDistance.value
  })

  const count = ref(15)

  const dispersalLabel = computed(() => {
    const preset = DISPERSAL_PRESETS.find((p) => p.id === dispersalPresetId.value)
    if (preset && preset.distance !== null) return preset.label
    return `Personalizado (${dispersalDistance.value} m)`
  })

  const analysis = ref<Analysis | null>(null)
  const result = computed(() => analysis.value?.result ?? null)
  const loading = ref(false)
  const apiError = ref<string | null>(null)
  const viewMode = ref<'baseline' | 'scenario'>('scenario')

  const projectMeta = reactive<ProjectMeta>({
    description: '',
    preparedBy: '',
  })

  const hasFootprint = computed(() => footprint.value.length >= 3)

  async function runAnalysis(parcelId: number | string): Promise<Analysis | null> {
    if (!hasFootprint.value) {
      analysis.value = null
      return null
    }
    loading.value = true
    try {
      const created = await api.createAnalysis(parcelId, {
        dispersalDistance: dispersalDistance.value,
        dispersalLabel: dispersalLabel.value,
        count: count.value,
        projectMeta: { ...projectMeta },
      })
      analysis.value = created
      apiError.value = null
      return created
    } catch (err) {
      analysis.value = null
      apiError.value = err instanceof Error ? err.message : 'No se pudo calcular el análisis de impacto'
      return null
    } finally {
      loading.value = false
    }
  }

  function setFootprint(polygon: { lat: number; lng: number }[]) {
    footprint.value = polygon
  }

  function reset() {
    footprint.value = []
    analysis.value = null
    apiError.value = null
  }

  return {
    footprint,
    dispersalPresetId,
    customDispersalDistance,
    dispersalDistance,
    dispersalLabel,
    count,
    result,
    loading,
    apiError,
    viewMode,
    projectMeta,
    hasFootprint,
    setFootprint,
    runAnalysis,
    reset,
  }
}
