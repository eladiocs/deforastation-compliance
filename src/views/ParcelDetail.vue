<script setup lang="ts">
import dayjs from 'dayjs'
import L from 'leaflet'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { Analysis, Parcel } from '@/api/types'
import AnalysisReport from '@/components/AnalysisReport.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EditParcelDialog from '@/components/EditParcelDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useParcelsStore } from '@/stores/parcels'
import { commodityLabel } from '@/utils/commodities'
import { addBaseLayers, geocodeCity } from '@/utils/mapLayers'
import { MagnifyingGlassIcon, PencilIcon, TrashIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const parcelId = route.params.id as string
const parcelsStore = useParcelsStore()

const parcel = ref<Parcel | null>(null)
const analyses = ref<Analysis[]>([])
const selectedAnalysis = ref<Analysis | null>(null)
const analysisPendingDeleteId = ref<string | null>(null)
const loading = ref(true)
const running = ref(false)
const error = ref<string | null>(null)

const cutoffDate = ref('2020-12-31')
const minTreeCoverPct = ref(10)
const showAdvanced = ref(false)

const citySearchQuery = ref('')
const isSearchingCity = ref(false)
const citySearchError = ref<string | null>(null)

let map: L.Map | undefined

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

async function load() {
  loading.value = true
  const [p, a] = await Promise.all([parcelsStore.fetchParcel(parcelId), parcelsStore.fetchAnalyses(parcelId)])
  parcel.value = p
  analyses.value = a
  loading.value = false
  await nextTick()
  renderMap(p)
}

function renderMap(p: Parcel) {
  const container = document.getElementById('parcel-map')
  if (!container) return
  container.innerHTML = ''
  map = L.map('parcel-map')
  addBaseLayers(map)
  const layer = L.geoJSON(p.geometry as any, { style: { color: '#059669', fillOpacity: 0.3 } }).addTo(map)
  map.fitBounds(layer.getBounds(), { padding: [5, 5], maxZoom: 17 })
}

async function runAnalysis() {
  running.value = true
  error.value = null
  try {
    const analysis = await parcelsStore.createAnalysis(parcelId, {
      cutoff_date: cutoffDate.value,
      min_tree_cover_pct: minTreeCoverPct.value,
    })
    analyses.value.unshift(analysis)
  } catch (e) {
    error.value = 'El análisis falló. Puede deberse a un error de Earth Engine o a una geometría demasiado grande.'
  } finally {
    running.value = false
  }
}

const analysisPendingDelete = computed(
  () => analyses.value.find((a) => a.id === analysisPendingDeleteId.value) ?? null,
)

function requestDeleteAnalysis(analysisId: string) {
  analysisPendingDeleteId.value = analysisId
}

function cancelDeleteAnalysis() {
  analysisPendingDeleteId.value = null
}

async function confirmDeleteAnalysis() {
  const analysisId = analysisPendingDeleteId.value
  if (analysisId) {
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

async function confirmEditParcel(payload: { name: string; clientName: string; commodity: string }) {
  isEditSaving.value = true
  editError.value = null
  try {
    parcel.value = await parcelsStore.updateParcel(parcelId, {
      name: payload.name,
      client_name: payload.clientName || null,
      commodity: payload.commodity,
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
    router.push(next ? `/parcels/${next.id}` : '/')
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
  <div v-if="loading" class="text-sm text-gray-500">Cargando…</div>
  <div v-else-if="parcel">
    <div class="mb-4 flex items-center gap-12">
      <div>
        <h1 class="text-xl font-semibold text-gray-900">{{ parcel.name }}</h1>
        <p class="text-sm text-gray-500">
          {{ parcel.client_name ?? 'Sin cliente asignado' }} · {{ commodityLabel(parcel.commodity) ?? 'Materia prima sin especificar' }}
        </p>
      </div>
      <div class="flex gap-2">
        <button
          type="button"
          title="Editar parcela"
          class="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-[#123a42]"
          @click="requestEditParcel"
        >
          <PencilIcon class="h-5 w-5 sm:h-6 sm:w-6" />
        </button>
        <button
          type="button"
          title="Eliminar parcela"
          class="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600"
          @click="requestDeleteParcel"
        >
          <TrashIcon class="h-5 w-5 sm:h-6 sm:w-6" />
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-[3fr_1fr]">
      <div class="relative isolate h-[360px] overflow-hidden rounded-xl border border-gray-200 lg:h-[58vh]">
        <div id="parcel-map" class="h-full w-full"></div>
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

      <div class="rounded-xl border border-gray-200 bg-white p-4">
        <h2 class="mb-2 text-sm font-semibold text-gray-900">Ejecutar análisis EUDR</h2>
        <button
          type="button"
          class="block text-xs text-gray-500 underline"
          @click="showAdvanced = !showAdvanced"
        >
          {{ showAdvanced ? 'Ocultar' : 'Mostrar' }} opciones avanzadas
        </button>
        <div v-if="showAdvanced" class="mt-3 space-y-3">
          <div>
            <label class="block text-xs font-medium text-gray-700">Fecha de corte</label>
            <input v-model="cutoffDate" type="date" class="mt-1 block w-full rounded-md border-gray-300 text-sm shadow-sm" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700">Umbral mínimo de cobertura arbórea (%)</label>
            <input
              v-model.number="minTreeCoverPct"
              type="number"
              min="0"
              max="100"
              class="mt-1 block w-full rounded-md border-gray-300 text-sm shadow-sm"
            />
          </div>
        </div>
        <button
          type="button"
          :disabled="running"
          class="mt-4 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
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
      description="Ejecuta el primer análisis EUDR para esta parcela."
    />
    <template v-else>
      <div class="space-y-3 md:hidden">
        <div v-for="a in analyses" :key="a.id" class="rounded-xl border border-gray-200 bg-white p-4">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium text-gray-900">{{ dayjs(a.created_at).format('DD/MM/YYYY HH:mm') }}</span>
            <StatusBadge :status="a.compliance_status" />
          </div>
          <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <div>
              <dt class="text-gray-500">Corte EUDR</dt>
              <dd class="text-gray-900">{{ a.cutoff_date }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Pérdida post-corte</dt>
              <dd class="text-gray-900">{{ a.loss_after_cutoff_area_ha.toFixed(2) }} ha</dd>
            </div>
          </dl>
          <div class="mt-3 flex items-center justify-end gap-2">
            <button
              type="button"
              class="rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
              @click="selectedAnalysis = a"
            >
              Ver análisis
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
              <th class="px-4 py-2 text-left font-medium text-gray-500">Corte EUDR</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Pérdida post-corte</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Estado</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500"></th>
              <th class="px-4 py-2 text-left font-medium text-gray-500"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="a in analyses" :key="a.id" class="hover:bg-gray-50">
              <td class="px-4 py-2 text-gray-600">{{ dayjs(a.created_at).format('DD/MM/YYYY HH:mm') }}</td>
              <td class="px-4 py-2 text-gray-600">{{ a.cutoff_date }}</td>
              <td class="px-4 py-2 text-gray-600">{{ a.loss_after_cutoff_area_ha.toFixed(2) }} ha</td>
              <td class="px-4 py-2"><StatusBadge :status="a.compliance_status" /></td>
              <td class="px-4 py-2 text-right">
                <button
                  type="button"
                  class="rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
                  @click="selectedAnalysis = a"
                >
                  Ver análisis
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

    <div
      v-if="selectedAnalysis"
      class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/40 px-4 py-8"
      @click.self="selectedAnalysis = null"
    >
      <div class="flex max-h-full w-full max-w-4xl flex-col rounded-xl bg-white shadow-xl">
        <div class="flex shrink-0 items-center justify-end border-b border-gray-200 p-2">
          <button
            type="button"
            class="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            @click="selectedAnalysis = null"
          >
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <div class="overflow-y-auto p-6">
          <AnalysisReport :analysis="selectedAnalysis" />
        </div>
        <div class="flex shrink-0 items-center justify-end border-t border-gray-200 p-2">
          <span class="invisible rounded-md p-1.5">
            <XMarkIcon class="h-5 w-5" />
          </span>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :open="!!analysisPendingDelete"
      title="Eliminar análisis"
      message="¿Seguro que quieres eliminar este análisis? Esta acción no se puede deshacer."
      confirm-label="Eliminar"
      @confirm="confirmDeleteAnalysis"
      @cancel="cancelDeleteAnalysis"
    />

    <EditParcelDialog
      :parcel="isEditDialogOpen ? parcel : null"
      :is-saving="isEditSaving"
      :save-error="editError"
      @confirm="confirmEditParcel"
      @cancel="cancelEditParcel"
    />

    <ConfirmDialog
      :open="isDeleteParcelDialogOpen"
      title="Eliminar parcela"
      :message="`¿Seguro que quieres eliminar ${parcel.name}? Esta acción no se puede deshacer.`"
      confirm-label="Eliminar"
      @confirm="confirmDeleteParcel"
      @cancel="cancelDeleteParcel"
    />
  </div>
</template>

<style scoped>
:deep(.leaflet-top.leaflet-right) {
  margin-top: 64px;
}
</style>
