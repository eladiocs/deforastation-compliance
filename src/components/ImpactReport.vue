<script setup lang="ts">
import { computed } from 'vue'
import * as api from '@/lib/api'
import type { ImpactAnalysisResult } from '@/types'
import type { ProjectMeta } from '@/composables/useImpactAnalysis'

const props = defineProps<{
  result: ImpactAnalysisResult
  analysisId: number
  parcelName: string
  projectMeta: ProjectMeta
  generatedAt: string
  dispersalLabel: string
}>()

const LEGEND_ITEMS = [
  { color: '#123a42', label: 'Parche de hábitat que sobrevive en el escenario con proyecto.' },
  { color: '#dc2626', label: 'Parche de hábitat perdido — su área se solapa con la huella del proyecto.' },
  { color: '#d97706', label: 'Parche recién aislado — sobrevive, pero se quedó sin ninguna ruta de dispersión viable.' },
  { color: '#5fb92c', label: 'Corredor sin afectar — su costo no cambió de forma significativa.' },
  { color: '#7c3aed', label: 'Corredor cortado — uno de los parches que conectaba fue destruido, o ya no existe ruta equivalente.' },
]

function nameFor(id: string): string {
  return props.result.patches.find((p) => p.id === id)?.name ?? id
}

const generatedAtLabel = computed(() => new Date(props.generatedAt).toLocaleString('es-ES'))
const reportUrl = computed(() => api.analysisReportUrl(props.analysisId))
</script>

<template>
  <div>
    <div class="no-print mb-4 flex flex-wrap items-center justify-end gap-2">
      <a
        :href="reportUrl"
        target="_blank"
        rel="noopener"
        class="rounded-md bg-[#5fb92c] px-3 py-1.5 text-sm font-medium text-white hover:bg-[#4ea023]"
      >
        Descargar PDF
      </a>
    </div>

    <div id="impact-report" class="space-y-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <header class="border-b border-gray-100 pb-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-[#5fb92c]">Informe de impacto</p>
        <h1 class="text-xl font-bold text-[#123a42]">
          {{ parcelName }}
        </h1>
        <p v-if="projectMeta.description" class="mt-1 text-sm text-gray-600">{{ projectMeta.description }}</p>
        <p class="mt-2 text-xs text-gray-400">
          Generado el {{ generatedAtLabel }}<span v-if="projectMeta.preparedBy"> · Elaborado por {{ projectMeta.preparedBy }}</span>
        </p>
      </header>

      <section>
        <h2 class="text-sm font-semibold text-[#123a42]">Metodología y supuestos</h2>
        <ul class="mt-1 list-inside list-disc text-sm text-gray-600">
          <li>Distancia de dispersión considerada: {{ dispersalLabel }}.</li>
          <li>
            Los datos de cobertura de suelo y zonas verdes combinan el mapa satelital ESA WorldCover (10 m, 2021)
            como fuente principal con datos de OpenStreetMap (caminos, cursos de agua y nombres de sitios). Ambas
            fuentes pueden no reflejar el estado actual del terreno (por ejemplo, WorldCover puede confundir
            plantaciones con bosque natural o no reflejar deforestación posterior a 2021), por lo que se recomienda
            validación de campo antes de su uso en un expediente formal.
          </li>
        </ul>
      </section>

      <section>
        <h2 class="text-sm font-semibold text-[#123a42]">Conectividad antes / después</h2>
        <table class="mt-2 w-full text-left text-sm">
          <thead>
            <tr class="border-b border-gray-200 text-xs uppercase text-gray-500">
              <th class="py-1">Métrica</th>
              <th class="py-1">Antes</th>
              <th class="py-1">Después</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-gray-100">
              <td class="py-1">Parches de hábitat</td>
              <td class="py-1">{{ result.baseline.metrics.totalPatches }}</td>
              <td class="py-1">{{ result.scenario.metrics.totalPatches }}</td>
            </tr>
            <tr class="border-b border-gray-100">
              <td class="py-1">Corredores</td>
              <td class="py-1">{{ result.baseline.metrics.totalCorridors }}</td>
              <td class="py-1">{{ result.scenario.metrics.totalCorridors }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="result.patchesLost.length">
        <h2 class="text-sm font-semibold text-red-700">Parches de hábitat perdidos</h2>
        <ul class="mt-1 list-inside list-disc text-sm text-gray-600">
          <li v-for="p in result.patchesLost" :key="p.id">{{ p.name }}</li>
        </ul>
      </section>

      <section v-if="result.corridorsLost.length">
        <h2 class="text-sm font-semibold text-violet-700">Corredores cortados</h2>
        <ul class="mt-1 list-inside list-disc text-sm text-gray-600">
          <li v-for="(e, i) in result.corridorsLost" :key="i">{{ nameFor(e.source) }} ↔ {{ nameFor(e.target) }}</li>
        </ul>
      </section>

      <section v-if="result.newlyIsolatedPatchIds.length">
        <h2 class="text-sm font-semibold text-amber-700">Parches recién aislados</h2>
        <p class="mt-1 text-sm text-gray-600">{{ result.newlyIsolatedPatchIds.map(nameFor).join(', ') }}</p>
      </section>

      <section>
        <h2 class="text-sm font-semibold text-[#123a42]">Cómo interpretar este informe</h2>
        <ul class="mt-2 space-y-1.5 text-sm text-gray-600">
          <li v-for="item in LEGEND_ITEMS" :key="item.label" class="flex items-start gap-2">
            <span class="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" :style="{ backgroundColor: item.color }"></span>
            <span>{{ item.label }}</span>
          </li>
        </ul>
        <p class="mt-3 text-sm text-gray-600">
          Un <strong>parche recién aislado</strong> es un parche que no fue destruido directamente por el proyecto,
          pero que quedó sin ninguna ruta de dispersión viable tras su construcción — suele ser la señal de impacto
          más crítica, porque puede aislar una población incluso sin ocupar su hábitat.
        </p>
      </section>

      <footer class="border-t border-gray-100 pt-3 text-xs text-gray-400">
        Este informe es una herramienta de apoyo técnico y no sustituye el criterio profesional ni la validación
        de campo requerida para un Estudio de Impacto Ambiental formal.
      </footer>
    </div>
  </div>
</template>
