import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, type CreateAnalysisPayload, type CreateParcelPayload, type UpdateParcelPayload } from '@/api/client'
import type { Analysis, Parcel } from '@/api/types'

export const useParcelsStore = defineStore('parcels', () => {
  const parcels = ref<Parcel[]>([])
  const analysesByParcel = ref<Record<string, Analysis[]>>({})
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastViewedMapCenter = ref<{ lat: number; lng: number; zoom: number } | null>(null)

  function setLastViewedMapCenter(center: { lat: number; lng: number; zoom: number }): void {
    lastViewedMapCenter.value = center
  }

  async function fetchParcels(): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      parcels.value = await api.listParcels()
    } catch {
      error.value = 'No se pudo conectar con la API. ¿Está el backend arrancado?'
    } finally {
      isLoading.value = false
    }
  }

  async function fetchParcel(parcelId: string): Promise<Parcel> {
    const parcel = await api.getParcel(parcelId)
    const index = parcels.value.findIndex((p) => p.id === parcelId)
    if (index === -1) {
      parcels.value = [...parcels.value, parcel]
    } else {
      parcels.value = parcels.value.map((p) => (p.id === parcelId ? parcel : p))
    }
    return parcel
  }

  async function createParcel(payload: CreateParcelPayload): Promise<Parcel> {
    const parcel = await api.createParcel(payload)
    parcels.value = [parcel, ...parcels.value]
    return parcel
  }

  async function updateParcel(parcelId: string, payload: UpdateParcelPayload): Promise<Parcel> {
    const parcel = await api.updateParcel(parcelId, payload)
    parcels.value = parcels.value.map((p) => (p.id === parcelId ? parcel : p))
    return parcel
  }

  async function deleteParcel(parcelId: string): Promise<void> {
    await api.deleteParcel(parcelId)
    parcels.value = parcels.value.filter((p) => p.id !== parcelId)
    const { [parcelId]: _removed, ...rest } = analysesByParcel.value
    analysesByParcel.value = rest
  }

  async function fetchAnalyses(parcelId: string): Promise<Analysis[]> {
    const analyses = await api.listParcelAnalyses(parcelId)
    analysesByParcel.value = { ...analysesByParcel.value, [parcelId]: analyses }
    return analyses
  }

  async function createAnalysis(parcelId: string, payload: CreateAnalysisPayload): Promise<Analysis> {
    const analysis = await api.createAnalysis(parcelId, payload)
    analysesByParcel.value = {
      ...analysesByParcel.value,
      [parcelId]: [analysis, ...(analysesByParcel.value[parcelId] ?? [])],
    }
    return analysis
  }

  async function deleteAnalysis(parcelId: string, analysisId: string): Promise<void> {
    await api.deleteAnalysis(analysisId)
    analysesByParcel.value = {
      ...analysesByParcel.value,
      [parcelId]: (analysesByParcel.value[parcelId] ?? []).filter((a) => a.id !== analysisId),
    }
  }

  return {
    parcels,
    analysesByParcel,
    isLoading,
    error,
    lastViewedMapCenter,
    setLastViewedMapCenter,
    fetchParcels,
    fetchParcel,
    createParcel,
    updateParcel,
    deleteParcel,
    fetchAnalyses,
    createAnalysis,
    deleteAnalysis,
  }
})
