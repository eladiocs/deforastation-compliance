<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PencilIcon, TrashIcon } from '@heroicons/vue/24/outline'
import FootprintMap from '@/components/FootprintMap.vue'
import ControlPanel from '@/components/ControlPanel.vue'
import ImpactReport from '@/components/ImpactReport.vue'
import ImpactStatusBadge from '@/components/ImpactStatusBadge.vue'
import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import BioEditParcelDialog from '@/components/BioEditParcelDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import * as api from '@/lib/api'
import { useImpactAnalysis } from '@/composables/useImpactAnalysis'
import { useBioParcelsStore } from '@/stores/bioParcels'
import { buildEdgeStatusMap, isolatedPatchIds, lostPatchIds } from '@/lib/impactView'
import type { Analysis, Parcel } from '@/types'

const zoom = 13

const route = useRoute()
const router = useRouter()
const parcelsStore = useBioParcelsStore()

const parcel = ref<Parcel | null>(null)
const loadingParcel = ref(true)
const loadError = ref<string | null>(null)

const analyses = ref<Analysis[]>([])
const activeAnalysis = ref<Analysis | null>(null)
const isReportOpen = ref(false)
const analysisPendingDeleteId = ref<number | null>(null)

const {
  dispersalPresetId,
  customDispersalDistance,
  count,
  loading,
  apiError,
  projectMeta,
  setFootprint,
  runAnalysis,
} = useImpactAnalysis()

const isEditDialogOpen = ref(false)
const isSavingEdit = ref(false)
const editError = ref<string | null>(null)

const isDeleteDialogOpen = ref(false)
const isDeleting = ref(false)

const center = computed<[number, number]>(() => {
  const f = parcel.value?.footprint ?? []
  if (!f.length) return [40.4168, -3.7038]
  return [
    f.reduce((sum, p) => sum + p.lat, 0) / f.length,
    f.reduce((sum, p) => sum + p.lng, 0) / f.length,
  ]
})

const activeResult = computed(() => activeAnalysis.value?.result ?? null)
const edgeStatus = computed(() => buildEdgeStatusMap(activeResult.value))
const lostIds = computed(() => lostPatchIds(activeResult.value))
const isolatedIds = computed(() => isolatedPatchIds(activeResult.value))

const analysisPendingDelete = computed(
  () => analyses.value.find((a) => a.id === analysisPendingDeleteId.value) ?? null,
)

async function loadParcel(id: string) {
  loadingParcel.value = true
  loadError.value = null
  try {
    const [p, history] = await Promise.all([api.getParcel(id), api.listAnalyses(id)])
    parcel.value = p
    analyses.value = history
    activeAnalysis.value = history[0] ?? null
    setFootprint(p.footprint)
  } catch {
    parcel.value = null
    loadError.value = 'No se pudo cargar la parcela.'
  } finally {
    loadingParcel.value = false
  }
}

onMounted(() => loadParcel(route.params.id as string))
watch(
  () => route.params.id,
  (id) => {
    if (id) loadParcel(id as string)
  },
)

async function handleGenerateAnalysis() {
  if (!parcel.value) return
  const created = await runAnalysis(parcel.value.id)
  if (created) {
    analyses.value.unshift(created)
    activeAnalysis.value = created
  }
}

function selectAnalysis(a: Analysis) {
  activeAnalysis.value = a
}

function viewAnalysis(a: Analysis) {
  activeAnalysis.value = a
  isReportOpen.value = true
}

function requestDeleteAnalysis(analysisId: number) {
  analysisPendingDeleteId.value = analysisId
}

function cancelDeleteAnalysis() {
  analysisPendingDeleteId.value = null
}

async function confirmDeleteAnalysis() {
  const analysisId = analysisPendingDeleteId.value
  if (analysisId) {
    await api.deleteAnalysis(analysisId)
    analyses.value = analyses.value.filter((a) => a.id !== analysisId)
    if (activeAnalysis.value?.id === analysisId) {
      activeAnalysis.value = analyses.value[0] ?? null
      isReportOpen.value = false
    }
  }
  analysisPendingDeleteId.value = null
}

function handleEditConfirm(payload: { name: string }) {
  if (!parcel.value) return
  isSavingEdit.value = true
  editError.value = null
  parcelsStore
    .updateParcel(parcel.value.id, payload.name)
    .then((updated) => {
      parcel.value = updated
      isEditDialogOpen.value = false
    })
    .catch(() => {
      editError.value = 'No se pudo guardar el nombre. Inténtalo de nuevo.'
    })
    .finally(() => {
      isSavingEdit.value = false
    })
}

function handleDeleteConfirm() {
  if (!parcel.value) return
  isDeleting.value = true
  parcelsStore
    .deleteParcel(parcel.value.id)
    .then(() => router.push('/corredores'))
    .finally(() => {
      isDeleting.value = false
      isDeleteDialogOpen.value = false
    })
}
</script>

<template>
  <EmptyState v-if="loadingParcel" title="Cargando parcela…" />
  <EmptyState v-else-if="loadError || !parcel" title="No se pudo conectar con la API" :description="loadError ?? 'Parcela no encontrada.'" />

  <template v-else>
    <div class="mb-4 flex items-center gap-12">
      <h1 class="truncate text-lg font-semibold text-[#123a42]">{{ parcel.name }}</h1>
      <div class="flex gap-2">
        <button
          type="button"
          title="Editar parcela"
          class="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-[#123a42]"
          @click="isEditDialogOpen = true"
        >
          <PencilIcon class="h-5 w-5 sm:h-6 sm:w-6" />
        </button>
        <button
          type="button"
          title="Eliminar parcela"
          class="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600"
          @click="isDeleteDialogOpen = true"
        >
          <TrashIcon class="h-5 w-5 sm:h-6 sm:w-6" />
        </button>
      </div>
    </div>

    <p v-if="apiError" class="mb-3 text-sm font-medium text-red-600">{{ apiError }}</p>

    <div class="no-print mb-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-[3fr_1fr]">
      <section class="space-y-3">
        <p v-if="activeAnalysis" class="text-xs text-gray-500">
          Mostrando análisis del
          <span class="font-medium text-gray-700">{{ new Date(activeAnalysis.createdAt).toLocaleString('es-ES') }}</span>
          · {{ activeAnalysis.dispersalLabel }}
        </p>
        <FootprintMap
          :patches="activeResult?.patches ?? []"
          :patches-lost-ids="lostIds"
          :patches-isolated-ids="isolatedIds"
          :edges="activeResult?.baseline.edges ?? []"
          :edge-status="edgeStatus"
          :footprint="parcel.footprint"
          :center="center"
          :zoom="zoom"
          :busy="loading"
          height-class="h-[310px] sm:h-[430px] lg:h-[540px]"
          readonly
        />
        <div class="flex flex-wrap gap-4 text-xs text-gray-500">
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-[#123a42]"></span> Parche de hábitat</span>
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-red-600"></span> Perdido por el proyecto</span>
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-amber-600"></span> Recién aislado</span>
          <span class="flex items-center gap-1"><span class="h-0.5 w-4 bg-violet-600"></span> Corredor cortado</span>
        </div>
      </section>

      <ControlPanel
        :dispersal-preset-id="dispersalPresetId"
        :custom-dispersal-distance="customDispersalDistance"
        :count="count"
        :project-meta="projectMeta"
        :busy="loading"
        @update:dispersal-preset-id="dispersalPresetId = $event"
        @update:custom-dispersal-distance="customDispersalDistance = $event"
        @update:count="count = $event"
        @generate-analysis="handleGenerateAnalysis"
      />
    </div>

    <h2 class="mb-2 text-sm font-semibold text-[#123a42]">Historial de análisis</h2>
    <EmptyState
      v-if="analyses.length === 0"
      title="Todavía no se ha ejecutado ningún análisis"
      description="Pulsa &quot;Generar análisis&quot; para calcular el impacto sobre los corredores biológicos."
    />
    <template v-else>
      <div class="space-y-3 md:hidden">
        <div
          v-for="a in analyses"
          :key="a.id"
          class="cursor-pointer rounded-lg border bg-white p-4"
          :class="a.id === activeAnalysis?.id ? 'border-[#123a42] ring-1 ring-[#123a42]' : 'border-gray-200'"
          @click="selectAnalysis(a)"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="flex items-center gap-2 text-sm font-medium text-[#123a42]">
              <span
                class="h-2 w-2 shrink-0 rounded-full"
                :class="a.id === activeAnalysis?.id ? 'bg-[#123a42]' : 'bg-gray-300'"
              ></span>
              {{ new Date(a.createdAt).toLocaleString('es-ES') }}
            </span>
            <ImpactStatusBadge :result="a.result" />
          </div>
          <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <div>
              <dt class="text-gray-500">Parches perdidos</dt>
              <dd class="text-gray-900">{{ a.result.patchesLost.length }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Corredores cortados</dt>
              <dd class="text-gray-900">{{ a.result.corridorsLost.length }}</dd>
            </div>
          </dl>
          <div class="mt-3 flex items-center justify-end gap-2">
            <button
              type="button"
              class="rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
              @click.stop="viewAnalysis(a)"
            >
              Ver análisis
            </button>
            <button
              type="button"
              title="Eliminar análisis"
              class="rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
              @click.stop="requestDeleteAnalysis(a.id)"
            >
              <TrashIcon class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div class="hidden w-full overflow-x-auto rounded-lg border border-gray-200 bg-white md:block">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Fecha</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Dispersión</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Parches perdidos</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Corredores cortados</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500">Estado</th>
              <th class="px-4 py-2 text-left font-medium text-gray-500"></th>
              <th class="px-4 py-2 text-left font-medium text-gray-500"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr
              v-for="a in analyses"
              :key="a.id"
              :class="a.id === activeAnalysis?.id ? 'bg-green-50' : 'hover:bg-gray-50'"
              @click="selectAnalysis(a)"
            >
              <td class="px-4 py-2 text-gray-600">
                <span class="flex items-center gap-2">
                  <span
                    class="h-2 w-2 shrink-0 rounded-full"
                    :class="a.id === activeAnalysis?.id ? 'bg-[#123a42]' : 'bg-gray-300'"
                  ></span>
                  {{ new Date(a.createdAt).toLocaleString('es-ES') }}
                </span>
              </td>
              <td class="px-4 py-2 text-gray-600">{{ a.dispersalLabel }}</td>
              <td class="px-4 py-2 text-gray-600">{{ a.result.patchesLost.length }}</td>
              <td class="px-4 py-2 text-gray-600">{{ a.result.corridorsLost.length }}</td>
              <td class="px-4 py-2"><ImpactStatusBadge :result="a.result" /></td>
              <td class="px-4 py-2 text-right">
                <button
                  type="button"
                  class="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
                  @click.stop="viewAnalysis(a)"
                >
                  Ver análisis
                </button>
              </td>
              <td class="px-4 py-2 text-right">
                <button
                  type="button"
                  title="Eliminar análisis"
                  class="rounded-md bg-white p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                  @click.stop="requestDeleteAnalysis(a.id)"
                >
                  <TrashIcon class="h-4 w-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <Modal :open="isReportOpen && !!activeAnalysis" max-width-class="max-w-4xl" @close="isReportOpen = false">
      <template #header>
        <h2 class="text-lg font-semibold text-gray-900">Informe de impacto</h2>
        <p class="mt-1 text-sm text-gray-500">{{ parcel.name }}</p>
      </template>
      <ImpactReport
        v-if="activeAnalysis"
        :result="activeAnalysis.result"
        :analysis-id="activeAnalysis.id"
        :parcel-name="parcel.name"
        :project-meta="activeAnalysis.projectMeta"
        :generated-at="activeAnalysis.createdAt"
        :dispersal-label="activeAnalysis.dispersalLabel"
      />
    </Modal>

    <BioEditParcelDialog
      :parcel="isEditDialogOpen ? parcel : null"
      :is-saving="isSavingEdit"
      :save-error="editError"
      @confirm="handleEditConfirm"
      @cancel="isEditDialogOpen = false"
    />
    <ConfirmDialog
      :open="isDeleteDialogOpen"
      title="Borrar parcela"
      :message="`¿Seguro que quieres borrar '${parcel.name}'? Esta acción no se puede deshacer.`"
      confirm-label="Borrar"
      @confirm="handleDeleteConfirm"
      @cancel="isDeleteDialogOpen = false"
    />
    <ConfirmDialog
      :open="!!analysisPendingDelete"
      title="Eliminar análisis"
      message="¿Seguro que quieres eliminar este análisis? Esta acción no se puede deshacer."
      confirm-label="Eliminar"
      @confirm="confirmDeleteAnalysis"
      @cancel="cancelDeleteAnalysis"
    />
  </template>
</template>
