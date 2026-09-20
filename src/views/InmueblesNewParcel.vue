<script setup lang="ts">
import L from 'leaflet'

import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { MagnifyingGlassIcon, MapPinIcon } from '@heroicons/vue/24/outline'

import { useInmueblesParcelsStore } from '@/stores/inmueblesParcels'
import type { GeoJsonPoint } from '@/api/inmueblesTypes'
import { addBaseLayers, geocodeCity } from '@/utils/mapLayers'
import InmueblesNewParcelDialog from '@/components/InmueblesNewParcelDialog.vue'

const parcelsStore = useInmueblesParcelsStore()

const router = useRouter()

const geometry = ref<GeoJsonPoint | null>(null)

const isDialogOpen = ref(false)
const submitting = ref(false)
const saveError = ref<string | null>(null)

const citySearchQuery = ref('')
const isSearchingCity = ref(false)
const citySearchError = ref<string | null>(null)

const coordsQuery = ref('')
const coordsError = ref<string | null>(null)

const isPlacingMode = ref(false)

let map: L.Map | undefined
let marker: L.Marker | undefined

function togglePlacingMode(): void {
  isPlacingMode.value = !isPlacingMode.value
  if (map) {
    map.getContainer().style.cursor = isPlacingMode.value ? 'crosshair' : ''
  }
}

async function searchCity() {
  const query = citySearchQuery.value.trim()
  if (!query) return
  isSearchingCity.value = true
  citySearchError.value = null
  try {
    const result = await geocodeCity(query)
    if (!result) {
      citySearchError.value = `No se ha encontrado "${query}"`
      return
    }
    map?.flyTo([result.lat, result.lon], 15)
  } catch {
    citySearchError.value = 'No se pudo buscar la ciudad. Inténtalo de nuevo.'
  } finally {
    isSearchingCity.value = false
  }
}

// Acepta "lat, lng" tal cual se copia desde Google Maps u otras herramientas
// GIS (con o sin espacio tras la coma).
const COORDS_PATTERN = /^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/

function goToCoordinates() {
  coordsError.value = null
  const match = coordsQuery.value.match(COORDS_PATTERN)
  if (!match) {
    coordsError.value = 'Formato esperado: latitud, longitud (ej. 39.4699, -0.3763)'
    return
  }
  const lat = Number(match[1])
  const lng = Number(match[2])
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    coordsError.value = 'Coordenadas fuera de rango'
    return
  }
  map?.flyTo([lat, lng], 17)
}

function placeMarker(lat: number, lng: number) {
  if (!map) return
  if (marker) {
    marker.setLatLng([lat, lng])
  } else {
    marker = L.marker([lat, lng], { draggable: true }).addTo(map)
    marker.on('dragend', () => {
      const pos = marker!.getLatLng()
      geometry.value = { type: 'Point', coordinates: [pos.lng, pos.lat] }
    })
  }
  geometry.value = { type: 'Point', coordinates: [lng, lat] }
}

function openDialogForNewGeometry(): void {
  saveError.value = null
  isDialogOpen.value = true
}

onMounted(() => {
  // Salento, Quindío (Eje Cafetero, Colombia) — mismo punto de partida que el
  // módulo de anti-deforestación cuando no hay una posición reciente guardada.
  const saved = parcelsStore.lastViewedMapCenter
  const initialCenter: L.LatLngTuple = saved ? [saved.lat, saved.lng] : [4.6357, -75.5701]
  const initialZoom = saved?.zoom ?? 15

  map = L.map('point-map').setView(initialCenter, initialZoom)
  map.on('moveend', () => {
    const center = map!.getCenter()
    parcelsStore.setLastViewedMapCenter({ lat: center.lat, lng: center.lng, zoom: map!.getZoom() })
  })
  addBaseLayers(map)

  map.on('click', (e: L.LeafletMouseEvent) => {
    if (!isPlacingMode.value) return
    placeMarker(e.latlng.lat, e.latlng.lng)
    openDialogForNewGeometry()
    isPlacingMode.value = false
    map!.getContainer().style.cursor = ''
  })
})

onUnmounted(() => {
  map?.remove()
})

async function handleConfirmDialog(payload: { name: string; address: string }) {
  if (!geometry.value) return
  submitting.value = true
  saveError.value = null
  try {
    const parcel = await parcelsStore.createParcel({
      name: payload.name,
      address: payload.address || null,
      geometry: geometry.value,
    })
    router.push(`/inmuebles/parcels/${parcel.id}`)
  } catch {
    saveError.value = 'No se pudo crear el inmueble. Inténtalo de nuevo.'
  } finally {
    submitting.value = false
  }
}

function handleCancelDialog(): void {
  saveError.value = null
  isDialogOpen.value = false
  geometry.value = null
  marker?.remove()
  marker = undefined
}
</script>

<template>
  <div>
    <h1 class="text-xl font-semibold text-gray-900">Nuevo inmueble</h1>

    <div class="mb-4 mt-1 flex flex-wrap items-center gap-3">
      <button
        type="button"
        class="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
        :class="
          isPlacingMode
            ? 'bg-[#5fb92c] text-white hover:bg-[#4ea023]'
            : 'border border-gray-300 text-gray-700 hover:bg-gray-100'
        "
        @click="togglePlacingMode"
      >
        <MapPinIcon class="h-4 w-4 shrink-0" />
        {{ isPlacingMode ? 'Cancelar' : 'Marcar ubicación en el mapa' }}
      </button>
      <p class="text-sm text-gray-500">
        <template v-if="isPlacingMode">Haz clic en el mapa para colocar el marcador.</template>
        <template v-else>
          Busca una ciudad o pega coordenadas para acercarte, luego pulsa el botón y haz clic en
          el mapa. Puedes arrastrar el marcador para ajustarlo.
        </template>
      </p>
    </div>

    <div class="relative isolate h-[320px] overflow-hidden rounded-xl border border-gray-200 sm:h-[480px] lg:h-[640px]">
      <div id="point-map" class="h-full w-full"></div>
      <div class="absolute right-3 top-3 z-[1000] flex flex-col items-end gap-1.5">
        <div class="flex gap-2.5">
          <form
            class="flex w-32 items-center gap-1 rounded-lg border border-gray-200 bg-white/95 px-2 py-1 shadow-sm backdrop-blur-sm transition-shadow focus-within:shadow-md sm:w-44 sm:gap-1.5 sm:px-2.5 sm:py-1.5"
            @submit.prevent="searchCity"
          >
            <span
              v-if="isSearchingCity"
              class="block h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent"
            />
            <MagnifyingGlassIcon v-else class="h-3.5 w-3.5 shrink-0 text-gray-400" />
            <input
              v-model="citySearchQuery"
              type="text"
              placeholder="Buscar ciudad..."
              class="min-w-0 flex-1 border-none bg-transparent p-0 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-0"
            />
          </form>

          <form
            class="flex w-28 items-center gap-1 rounded-lg border border-gray-200 bg-white/95 px-2 py-1 shadow-sm backdrop-blur-sm transition-shadow focus-within:shadow-md sm:w-40 sm:gap-1.5 sm:px-2.5 sm:py-1.5"
            @submit.prevent="goToCoordinates"
          >
            <MapPinIcon class="h-3.5 w-3.5 shrink-0 text-gray-400" />
            <input
              v-model="coordsQuery"
              type="text"
              placeholder="lat, lng..."
              class="min-w-0 flex-1 border-none bg-transparent p-0 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-0"
            />
          </form>
        </div>
        <p v-if="citySearchError" class="rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800 shadow-sm">
          {{ citySearchError }}
        </p>
        <p v-if="coordsError" class="rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800 shadow-sm">
          {{ coordsError }}
        </p>
      </div>
    </div>

    <InmueblesNewParcelDialog
      :open="isDialogOpen"
      :is-saving="submitting"
      :save-error="saveError"
      @confirm="handleConfirmDialog"
      @cancel="handleCancelDialog"
    />
  </div>
</template>

<style scoped>
:deep(.leaflet-top.leaflet-right) {
  margin-top: 48px;
}
</style>
