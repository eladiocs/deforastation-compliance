<script setup lang="ts">
import dayjs from 'dayjs'
import L from 'leaflet'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { Analysis, Parcel } from '@/api/inmueblesTypes'
import InmueblesAnalysisReport from '@/components/InmueblesAnalysisReport.vue'
import InmueblesEditParcelDialog from '@/components/InmueblesEditParcelDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import RiskBadge from '@/components/RiskBadge.vue'
import { useInmueblesParcelsStore } from '@/stores/inmueblesParcels'
import { addBaseLayers } from '@/utils/mapLayers'
import { PencilIcon, TrashIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const parcelId = Number(route.params.id)
const parcelsStore = useInmueblesParcelsStore()

const parcel = ref<Parcel | null>(null)
const analyses = ref<Analysis[]>([])
const selectedAnalysis = ref<Analysis | null>(null)
const analysisPendingDeleteId = ref<number | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const running = ref(false)
const error = ref<string | null>(null)

const bufferRadiusM = ref(300)

let map: L.Map | undefined
let bufferCircle: L.Circle | undefined

async function load() {
  loading.value = true
  loadError.value = null
  try {
    const [p, a] = await Promise.all([parcelsStore.fetchParcel(parcelId), parcelsStore.fetchAnalyses(parcelId)])
    parcel.value = p
    analyses.value = a
    loading.value = false
    await nextTick()
    renderMap(p)
  } catch {
    loadError.value = '¿Está el backend arrancado? Recarga la página para volver a intentarlo.'
    loading.value = false
  }
}

function renderMap(p: Parcel) {
  const container = document.getElementById('parcel-map')
  if (!container) return
  container.innerHTML = ''
  const [lng, lat] = p.geometry.coordinates
  map = L.map('parcel-map').setView([lat, lng], 15)
  addBaseLayers(map)
  L.marker([lat, lng]).addTo(map)
  bufferCircle = L.circle([lat, lng], {
    radius: bufferRadiusM.value,
    color: '#5fb92c',
    fillOpacity: 0.1,
  }).addTo(map)
  map.on('moveend', () => {
    const center = map!.getCenter()
    parcelsStore.setLastViewedMapCenter({ lat: center.lat, lng: center.lng, zoom: map!.getZoom() })
  })
}

function updateBufferCircle() {
  bufferCircle?.setRadius(bufferRadiusM.value)
}

async function runAnalysis() {
  if (bufferRadiusM.value < 50) {
    error.value = 'El radio debe ser como mínimo 50 metros.'
    return
  }
  running.value = true
  error.value = null
  try {
    const analysis = await parcelsStore.createAnalysis(parcelId, {
      buffer_radius_m: bufferRadiusM.value,
    })
    analyses.value.unshift(analysis)
  } catch {
    error.value = 'El análisis falló. Puede deberse a un error de Earth Engine o a un radio demasiado grande.'
  } finally {
    running.value = false
  }
}

const analysisPendingDelete = computed(
  () => analyses.value.find((a) => a.id === analysisPendingDeleteId.value) ?? null,
)

function requestDeleteAnalysis(analysisId: number) {
  analysisPendingDeleteId.value = analysisId
}

function cancelDeleteAnalysis() {
  analysisPendingDeleteId.value = null
}

async function confirmDeleteAnalysis() {
  const analysisId = analysisPendingDeleteId.value
  if (analysisId !== null) {
    await parcelsStore.deleteAnalysis(parcelId, analysisId)
    analyses.value = analyses.value.filter((a) => a.id !== analysisId)
    if (selectedAnalysis.value?.id === analysisId) {
      selectedAnalysis.value = null
    }
  }
  analysisPendingDeleteId.value = null
}

const isEditDialogOpen = ref(false)
const isEditSaving = ref(false)
const editError = ref<string | null>(null)

function requestEditParcel() {
  editError.value = null
  isEditDialogOpen.value = true
}

function cancelEditParcel() {
  isEditDialogOpen.value = false
}

async function confirmEditParcel(payload: { name: string; address: string }) {
  isEditSaving.value = true
  editError.value = null
  try {
    parcel.value = await parcelsStore.updateParcel(parcelId, {
      name: payload.name,
      address: payload.address || null,
    })
    isEditDialogOpen.value = false
  } catch {
    editError.value = 'No se pudo guardar los cambios. Inténtalo de nuevo.'
  } finally {
    isEditSaving.value = false
  }
}

const isDeleteParcelDialogOpen = ref(false)
const isDeletingParcel = ref(false)

function requestDeleteParcel() {
  isDeleteParcelDialogOpen.value = true
}

function cancelDeleteParcel() {
  isDeleteParcelDialogOpen.value = false
}

async function confirmDeleteParcel() {
  isDeletingParcel.value = true
  try {
    await parcelsStore.deleteParcel(parcelId)
    isDeleteParcelDialogOpen.value = false
    const next = parcelsStore.parcels[0]
    router.push(next ? `/inmuebles/parcels/${next.id}` : '/inmuebles')
  } finally {
    isDeletingParcel.value = false
  }
}

onMounted(load)
onUnmounted(() => {
  map?.remove()
})
</script>

<template>
  <EmptyState v-if="loading" title="Cargando inmueble…" />
  <EmptyState v-else-if="loadError" title="No se pudo conectar con la API" :description="loadError" />
  <div v-else-if="parcel">
    <div class="mb-4 flex items-center gap-12">
      <div>
        <h1 class="text-xl font-semibold text-gray-900">{{ parcel.name }}</h1>
        <p class="text-sm text-gray-500">
          {{ parcel.address ?? 'Sin dirección especificada' }}
        </p>
      </div>
      <div class="flex gap-2">
        <button
          type="button"
          title="Editar inmueble"
          class="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-[#123a42]"
          @click="requestEditParcel"
        >
          <PencilIcon class="h-5 w-5 sm:h-6 sm:w-6" />
        </button>
        <button
          type="button"
          title="Eliminar inmueble"
          class="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600"
          @click="requestDeleteParcel"
        >
          <TrashIcon class="h-5 w-5 sm:h-6 sm:w-6" />
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-[3fr_1fr]">
      <div class="relative isolate h-[300px] overflow-hidden rounded-xl border border-gray-200 sm:h-[440px] lg:h-[580px]">
        <div id="parcel-map" class="h-full w-full"></div>
      </div>

      <div class="rounded-xl border border-gray-200 bg-white p-4">
        <h2 class="mb-2 text-sm font-semibold text-gray-900">Ejecutar análisis de riesgo</h2>
        <div>
          <label class="block text-xs font-medium text-gray-700">Radio de análisis (m)</label>
          <input
            v-model.number="bufferRadiusM"
            type="number"
            min="50"
            max="2000"
            step="50"
            class="mt-1 block w-full rounded-md border-gray-300 text-sm shadow-sm"
            @change="updateBufferCircle"
          />
        </div>
        <button
          type="button"
          :disabled="running"
          class="mt-4 rounded-md bg-[#5fb92c] px-4 py-2 text-sm font-medium text-white hover:bg-[#4ea023] disabled:opacity-50"
          @click="runAnalysis"
        >
          {{ running ? 'Analizando (puede tardar hasta un minuto)…' : 'Ejecutar nuevo análisis' }}
        </button>
        <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
      </div>
    </div>

    <h2 class="mb-2 mt-8 text-sm font-semibold text-gray-900">Historial de análisis</h2>
    <EmptyState
      v-if="analyses.length === 0"
      title="Todavía no se ha ejecutado ningún análisis"
      description="Ejecuta el primer análisis de riesgo de inundación para este inmueble."
    />
    <template v-else>
      <div class="space-y-3 md:hidden">
        <div v-for="a in analyses" :key="a.id" class="rounded-xl border border-gray-200 bg-white p-4">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium text-gray-900">{{ dayjs(a.created_at).format('DD/MM/YYYY HH:mm') }}</span>
            <RiskBadge :label="a.risk_label" />
          </div>
          <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <div>
              <dt class="text-gray-500">Score</dt>
              <dd class="text-gray-900">{{ a.risk_score.toFixed(0) }} / 100</dd>
            </div>
            <div>
              <dt class="text-gray-500">Radio</dt>
              <dd class="text-gray-900">{{ a.buffer_radius_m.toFixed(0) }} m</dd>
            </div>
          </dl>
          <div class="mt-3 flex items-center justify-end gap-2">
            <button
              type="button"
              class="rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
              @click="selectedAnalysis = a"
            >
              Ver informe
            </button>
            <button
              type="button"
              title="Eliminar análisis"
              class="rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
              @click="requestDeleteAnalysis(a.id)"
            >
              <TrashIcon class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div class="hidden w-full overflow-x-auto rounded-xl border border-gray-200 bg-white md:block lg:w-3/4">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Fecha</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Score</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Radio</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Riesgo</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500"></th>
              <th class="px-4 py-2 text-left font-medium text-gray-500"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="a in analyses" :key="a.id" class="hover:bg-gray-50">
              <td class="px-4 py-2 text-gray-600">{{ dayjs(a.created_at).format('DD/MM/YYYY HH:mm') }}</td>
              <td class="px-4 py-2 text-gray-600">{{ a.risk_score.toFixed(0) }} / 100</td>
              <td class="px-4 py-2 text-gray-600">{{ a.buffer_radius_m.toFixed(0) }} m</td>
              <td class="px-4 py-2"><RiskBadge :label="a.risk_label" /></td>
              <td class="px-4 py-2 text-right">
                <button
                  type="button"
                  class="rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
                  @click="selectedAnalysis = a"
                >
                  Ver informe
                </button>
              </td>
              <td class="px-4 py-2 text-right">
                <button
                  type="button"
                  title="Eliminar análisis"
                  class="rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                  @click="requestDeleteAnalysis(a.id)"
                >
                  <TrashIcon class="h-4 w-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <Modal :open="!!selectedAnalysis" max-width-class="max-w-4xl" @close="selectedAnalysis = null">
      <template #header>
        <h2 class="text-lg font-semibold text-gray-900">Informe de riesgo de inundación</h2>
        <p v-if="selectedAnalysis" class="mt-1 text-sm text-gray-500">
          {{ dayjs(selectedAnalysis.created_at).format('DD/MM/YYYY HH:mm') }}
        </p>
      </template>
      <InmueblesAnalysisReport v-if="selectedAnalysis" :analysis="selectedAnalysis" />
    </Modal>

    <ConfirmDialog
      :open="!!analysisPendingDelete"
      title="Eliminar análisis"
      message="¿Seguro que quieres eliminar este análisis? Esta acción no se puede deshacer."
      confirm-label="Eliminar"
      @confirm="confirmDeleteAnalysis"
      @cancel="cancelDeleteAnalysis"
    />

    <InmueblesEditParcelDialog
      :parcel="isEditDialogOpen ? parcel : null"
      :is-saving="isEditSaving"
      :save-error="editError"
      @confirm="confirmEditParcel"
      @cancel="cancelEditParcel"
    />

    <ConfirmDialog
      :open="isDeleteParcelDialogOpen"
      title="Eliminar inmueble"
      :message="`¿Seguro que quieres eliminar ${parcel.name}? Esta acción no se puede deshacer.`"
      confirm-label="Eliminar"
      @confirm="confirmDeleteParcel"
      @cancel="cancelDeleteParcel"
    />
  </div>
</template>
