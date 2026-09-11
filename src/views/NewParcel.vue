<script setup lang="ts">
import L from 'leaflet'
import 'leaflet-draw'

import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline'

import { useParcelsStore } from '@/stores/parcels'
import type { GeoJsonPolygon } from '@/api/types'
import { addBaseLayers, geocodeCity } from '@/utils/mapLayers'
import NewParcelDialog from '@/components/NewParcelDialog.vue'

const parcelsStore = useParcelsStore()

const router = useRouter()

const geometry = ref<GeoJsonPolygon | null>(null)
const error = ref<string | null>(null)

const isDialogOpen = ref(false)
const submitting = ref(false)
const saveError = ref<string | null>(null)

const citySearchQuery = ref('')
const isSearchingCity = ref(false)
const citySearchError = ref<string | null>(null)

let map: L.Map | undefined
let drawnLayer: L.FeatureGroup

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
    map?.flyTo([result.lat, result.lon], 12)
  } catch {
    citySearchError.value = 'No se pudo buscar la ciudad. Inténtalo de nuevo.'
  } finally {
    isSearchingCity.value = false
  }
}

function updateGeometryFromLayer() {
  const layers = drawnLayer.getLayers()
  if (layers.length === 0) {
    geometry.value = null
    return
  }
  const geojson = (layers[0] as L.Polygon).toGeoJSON()
  geometry.value = geojson.geometry as GeoJsonPolygon
}

function openDialogForNewGeometry(): void {
  error.value = null
  saveError.value = null
  isDialogOpen.value = true
}

onMounted(() => {
  // Salento, Quindío (Eje Cafetero, Colombia) — zona cafetera, a nivel de parcela
  map = L.map('draw-map').setView([4.6357, -75.5701], 17)
  addBaseLayers(map)

  drawnLayer = new L.FeatureGroup()
  map.addLayer(drawnLayer)

  const drawControl = new L.Control.Draw({
    draw: {
      polygon: {},
      polyline: false,
      rectangle: false,
      circle: false,
      circlemarker: false,
      marker: false,
    },
    // leaflet-draw supports edit:false to hide the edit/delete toolbar; @types/leaflet-draw doesn't model it
    edit: false as unknown as L.Control.EditOptions,
  })
  map.addControl(drawControl)

  map.on(L.Draw.Event.CREATED, (e: any) => {
    drawnLayer.clearLayers()
    drawnLayer.addLayer(e.layer)
    updateGeometryFromLayer()
    openDialogForNewGeometry()
  })
})

onUnmounted(() => {
  map?.remove()
})

function extractPolygonGeometry(parsed: any): GeoJsonPolygon | null {
  if (parsed.type === 'FeatureCollection') {
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
  return parsed.type === 'Feature' ? parsed.geometry : parsed
}

function onFileUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const parsed = JSON.parse(reader.result as string)
      const geom = extractPolygonGeometry(parsed)
      if (!geom || (geom.type !== 'Polygon' && geom.type !== 'MultiPolygon')) {
        error.value = 'El archivo debe contener un Polygon o MultiPolygon GeoJSON.'
        return
      }
      geometry.value = geom
      drawnLayer.clearLayers()
      const layer = L.geoJSON(geom)
      layer.eachLayer((l) => drawnLayer.addLayer(l))
      map?.fitBounds(layer.getBounds(), { padding: [5, 5], maxZoom: 17 })
      openDialogForNewGeometry()
    } catch {
      error.value = 'No se pudo leer el archivo como GeoJSON válido.'
    }
  }
  reader.readAsText(file)
}

async function handleConfirmDialog(payload: { name: string; clientName: string; commodity: string }) {
  if (!geometry.value) return
  submitting.value = true
  saveError.value = null
  try {
    const parcel = await parcelsStore.createParcel({
      name: payload.name,
      client_name: payload.clientName || null,
      commodity: payload.commodity || null,
      geometry: geometry.value,
    })
    router.push(`/parcels/${parcel.id}`)
  } catch (e) {
    saveError.value = 'No se pudo crear la parcela. Revisa que la geometría sea válida.'
  } finally {
    submitting.value = false
  }
}

function handleCancelDialog(): void {
  saveError.value = null
  isDialogOpen.value = false
  geometry.value = null
  drawnLayer.clearLayers()
}
</script>

<template>
  <div>
    <h1 class="mb-4 text-xl font-semibold text-gray-900">Nueva parcela</h1>

    <div class="mb-3 flex flex-wrap items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      <span class="text-sm text-gray-600">Dibuje su polígono o suba un geojson</span>
      <input
        type="file"
        accept=".geojson,.json,application/geo+json"
        class="text-sm"
        @change="onFileUpload"
      />
    </div>

    <p v-if="error" class="mb-3 text-sm text-red-600">{{ error }}</p>

    <div class="relative isolate h-[360px] overflow-hidden rounded-xl border border-gray-200 lg:h-[58vh]">
      <div id="draw-map" class="h-full w-full"></div>
      <form
        class="absolute right-3 top-3 z-[1000] flex w-40 items-center gap-1.5 rounded-lg border border-gray-200 bg-white/95 px-2.5 py-1.5 shadow-sm backdrop-blur-sm transition-shadow focus-within:shadow-md sm:w-52"
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
          class="min-w-0 flex-1 border-none bg-transparent text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-0"
        />
      </form>
      <div
        v-if="citySearchError"
        class="absolute right-3 top-14 z-[1000] rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800 shadow-sm"
      >
        {{ citySearchError }}
      </div>
    </div>

    <NewParcelDialog
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
  margin-top: 64px;
}
</style>
