import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/lib/api'
import type { Parcel } from '@/types'

export const useBioParcelsStore = defineStore('bioParcels', () => {
  const parcels = ref<Parcel[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchParcels() {
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

  async function createParcel(name: string, footprint: { lat: number; lng: number }[]): Promise<Parcel> {
    const parcel = await api.createParcel(name, footprint)
    parcels.value = [parcel, ...parcels.value]
    return parcel
  }

  async function updateParcel(id: number, name: string): Promise<Parcel> {
    const parcel = await api.updateParcel(id, name)
    parcels.value = parcels.value.map((p) => (p.id === id ? parcel : p))
    return parcel
  }

  async function deleteParcel(id: number): Promise<void> {
    await api.deleteParcel(id)
    parcels.value = parcels.value.filter((p) => p.id !== id)
  }

  return { parcels, isLoading, error, fetchParcels, createParcel, updateParcel, deleteParcel }
})
