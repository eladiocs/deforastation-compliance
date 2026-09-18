<script setup lang="ts">
import L from 'leaflet'
import 'leaflet-draw'
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline'
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { addBaseLayers, geocodeCity } from '@/lib/mapLayers'
import { extractPolygonGeometry, largestRing } from '@/lib/geojson'
import type { CorridorEdge, Patch } from '@/types'

export type EdgeStatus = 'lost' | 'unaffected'

const props = withDefaults(
  defineProps<{
    patches: Patch[]
    patchesLostIds: Set<string>
    patchesIsolatedIds: Set<string>
    edges: CorridorEdge[]
    edgeStatus: Map<string, EdgeStatus>
    footprint: { lat: number; lng: number }[]
    center: [number, number]
    zoom: number
    busy?: boolean
    busyLabel?: string
    readonly?: boolean
    heightClass?: string
  }>(),
  {
    busy: false,
    busyLabel: 'Calculando impacto…',
    readonly: false,
    heightClass: 'h-[320px] sm:h-[480px] lg:h-[640px]',
  },
)

const emit = defineEmits<{
  footprintDefined: [polygon: { lat: number; lng: number }[]]
  fileUploaded: [name: string]
}>()

const mapContainer = ref<HTMLDivElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploadError = ref<string | null>(null)
const citySearchQuery = ref('')
const isSearchingCity = ref(false)
const citySearchError = ref<string | null>(null)

let nativeMap: L.Map | undefined
let drawnLayer: L.FeatureGroup | undefined
let patchesLayer: L.LayerGroup | undefined
let edgesLayer: L.LayerGroup | undefined
let footprintLayer: L.FeatureGroup | undefined

function patchById(id: string): Patch | undefined {
  return props.patches.find((p) => p.id === id)
}

function edgeLatLngs(edge: CorridorEdge): [number, number][] {
  if (edge.route.length) return edge.route.map((p) => [p.lat, p.lng])
  const source = patchById(edge.source)
  const target = patchById(edge.target)
  return [
    [source?.lat ?? 0, source?.lng ?? 0],
    [target?.lat ?? 0, target?.lng ?? 0],
  ]
}

function edgeKey(a: string, b: string): string {
  return a < b ? `${a}|${b}` : `${b}|${a}`
}

function edgeStyle(edge: CorridorEdge) {
  const status = props.edgeStatus.get(edgeKey(edge.source, edge.target)) ?? 'unaffected'
  if (status === 'lost') return { color: '#7c3aed', weight: 3, opacity: 0.9, dashArray: '6 6' }
  return { color: '#5fb92c', weight: 1.5, opacity: 0.5 }
}

function patchColor(patch: Patch): string {
  if (props.patchesLostIds.has(patch.id)) return '#dc2626'
  if (props.patchesIsolatedIds.has(patch.id)) return '#d97706'
  return '#123a42'
}

function renderPatches() {
  if (!patchesLayer) return
  patchesLayer.clearLayers()
  for (const patch of props.patches) {
    const color = patchColor(patch)
    L.circle([patch.lat, patch.lng], {
      radius: patch.radius,
      color,
      weight: 1,
      fillColor: color,
      fillOpacity: 0.7,
    })
      .bindTooltip(patch.name, { direction: 'top' })
      .addTo(patchesLayer)
  }
}

function renderEdges() {
  if (!edgesLayer) return
  edgesLayer.clearLayers()
  for (const edge of props.edges) {
    const style = edgeStyle(edge)
    L.polyline(edgeLatLngs(edge), style).addTo(edgesLayer)
  }
}

function renderFootprint() {
  if (!footprintLayer) return
  footprintLayer.clearLayers()
  if (props.footprint.length >= 3) {
    L.polygon(
      props.footprint.map((p) => [p.lat, p.lng] as [number, number]),
      { color: '#eab308', weight: 2.5, fillColor: '#eab308', fillOpacity: 0.12 },
    ).addTo(footprintLayer)
  }
}

function emitRing(ring: { lat: number; lng: number }[]) {
  emit('footprintDefined', ring)
}

function initMap() {
  if (!mapContainer.value || nativeMap) return

  nativeMap = L.map(mapContainer.value).setView(props.center, props.zoom)
  addBaseLayers(nativeMap)

  patchesLayer = L.layerGroup().addTo(nativeMap)
  edgesLayer = L.layerGroup().addTo(nativeMap)
  footprintLayer = L.featureGroup().addTo(nativeMap)
  renderPatches()
  renderEdges()
  renderFootprint()

  if (props.footprint.length >= 3) {
    nativeMap.fitBounds(footprintLayer.getBounds(), { padding: [20, 20], maxZoom: 17 })
  }

  if (props.readonly) return

  drawnLayer = L.featureGroup().addTo(nativeMap)

  const drawControl = new L.Control.Draw({
    draw: {
      polygon: {},
      polyline: false,
      rectangle: false,
      circle: false,
      circlemarker: false,
      marker: false,
    },
    edit: false as unknown as L.Control.EditOptions,
  })
  nativeMap.addControl(drawControl)

  nativeMap.on(L.Draw.Event.CREATED, (e: any) => {
    uploadError.value = null
    drawnLayer?.clearLayers()
    drawnLayer?.addLayer(e.layer)
    const geometry = (e.layer as L.Polygon).toGeoJSON().geometry
    emitRing(largestRing(geometry as any))
  })
}

function triggerFileUpload() {
  fileInputRef.value?.click()
}

function onFileUpload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file || !nativeMap || !drawnLayer) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const parsed = JSON.parse(reader.result as string)
      const geometry = extractPolygonGeometry(parsed)
      if (!geometry) {
        uploadError.value = 'El archivo debe contener un Polygon o MultiPolygon GeoJSON.'
        return
      }
      uploadError.value = null
      drawnLayer!.clearLayers()
      const layer = L.geoJSON(geometry as any)
      layer.eachLayer((l) => drawnLayer!.addLayer(l))
      nativeMap!.fitBounds(layer.getBounds(), { padding: [20, 20], maxZoom: 17 })
      emitRing(largestRing(geometry))
      emit('fileUploaded', file.name)
    } catch {
      uploadError.value = 'No se pudo leer el archivo como GeoJSON válido.'
    }
  }
  reader.readAsText(file)
}

async function searchCity() {
  const query = citySearchQuery.value.trim()
  if (!query || !nativeMap) return
  isSearchingCity.value = true
  citySearchError.value = null
  try {
    const result = await geocodeCity(query)
    if (!result) {
      citySearchError.value = `No se ha encontrado "${query}"`
      return
    }
    nativeMap.flyTo([result.lat, result.lon], 14)
  } catch {
    citySearchError.value = 'No se pudo buscar. Inténtalo de nuevo.'
  } finally {
    isSearchingCity.value = false
  }
}

function clearDrawing() {
  drawnLayer?.clearLayers()
  uploadError.value = null
}

defineExpose({ clearDrawing, triggerFileUpload })

onMounted(() => {
  nextTick(initMap)
})

onUnmounted(() => {
  nativeMap?.remove()
  nativeMap = undefined
})

watch(() => [props.patches, props.patchesLostIds, props.patchesIsolatedIds], renderPatches)
watch(() => [props.edges, props.edgeStatus], renderEdges)
watch(() => props.footprint, renderFootprint)
</script>

<template>
  <div class="space-y-2">
    <p v-if="uploadError" class="text-sm text-red-600">{{ uploadError }}</p>

    <div class="relative isolate w-full overflow-hidden rounded-lg border border-gray-200" :class="heightClass">
      <div ref="mapContainer" class="h-full w-full"></div>

      <form
        v-if="!readonly"
        class="absolute right-3 top-3 z-[1000] flex w-40 items-center gap-1.5 rounded-lg border border-gray-200 bg-white/95 px-2.5 py-1.5 shadow-sm backdrop-blur-sm sm:w-52"
        @submit.prevent="searchCity"
      >
        <span
          v-if="isSearchingCity"
          class="block h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-[#5fb92c] border-t-transparent"
        />
        <MagnifyingGlassIcon v-else class="h-3.5 w-3.5 shrink-0 text-gray-400" />
        <input
          v-model="citySearchQuery"
          type="text"
          placeholder="Buscar ciudad…"
          class="min-w-0 flex-1 border-none bg-transparent p-0 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-0"
        />
      </form>
      <div
        v-if="citySearchError"
        class="absolute right-3 top-14 z-[1000] rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800 shadow-sm"
      >
        {{ citySearchError }}
      </div>

      <input
        v-if="!readonly"
        ref="fileInputRef"
        type="file"
        accept=".geojson,.json,application/geo+json"
        class="hidden"
        @change="onFileUpload"
      />

      <div
        v-if="busy"
        class="absolute inset-0 z-[900] flex items-center justify-center bg-slate-900/40 backdrop-blur-[1px]"
      >
        <div class="flex items-center gap-2 rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow">
          <span class="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-[#5fb92c]"></span>
          {{ busyLabel }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.leaflet-top.leaflet-right) {
  margin-top: 56px;
}
</style>
