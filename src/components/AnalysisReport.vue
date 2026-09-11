<script setup lang="ts">
import dayjs from 'dayjs'

import { api } from '@/api/client'
import type { Analysis } from '@/api/types'
import BarChart from '@/components/BarChart.vue'
import LineChart from '@/components/LineChart.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const props = defineProps<{
  analysis: Analysis
}>()

const lossLabels = () => props.analysis.yearly_loss_since_2001.map((d) => d.year)
const lossValues = () => props.analysis.yearly_loss_since_2001.map((d) => d.area_ha)

const ndviLabels = () => props.analysis.ndvi_quarterly_series.map((p) => dayjs(p.period_start).format('YYYY-MM'))
const ndviValues = () => props.analysis.ndvi_quarterly_series.map((p) => p.ndvi_mean)
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-gray-900">Informe de análisis</h1>
        <p class="text-sm text-gray-500">{{ dayjs(analysis.created_at).format('DD/MM/YYYY HH:mm') }}</p>
      </div>
      <a
        :href="api.reportUrl(analysis.id)"
        target="_blank"
        rel="noopener"
        class="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
      >
        Descargar
      </a>
    </div>

    <div class="mb-6 rounded-xl border border-gray-200 bg-white p-4">
      <StatusBadge :status="analysis.compliance_status" />
      <div class="mt-3 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
        <div>
          <p class="text-gray-500">Superficie total</p>
          <p class="font-medium text-gray-900">{{ analysis.parcel_area_ha.toFixed(2) }} ha</p>
        </div>
        <div>
          <p class="text-gray-500">Bosque base (2000)</p>
          <p class="font-medium text-gray-900">{{ analysis.baseline_forest_area_ha.toFixed(2) }} ha</p>
        </div>
        <div>
          <p class="text-gray-500">Pérdida tras el corte</p>
          <p class="font-medium text-gray-900">{{ analysis.loss_after_cutoff_area_ha.toFixed(2) }} ha</p>
        </div>
        <div>
          <p class="text-gray-500">Fecha de corte</p>
          <p class="font-medium text-gray-900">{{ analysis.cutoff_date }}</p>
        </div>
      </div>
    </div>

    <h2 class="mb-2 text-sm font-semibold text-gray-900">Pérdida de cobertura forestal por año</h2>
    <div class="mb-6 rounded-xl border border-gray-200 bg-white p-4">
      <BarChart
        :labels="lossLabels()"
        :values="lossValues()"
        :highlight-from="analysis.cutoff_date ? Number(analysis.cutoff_date.slice(0, 4)) + 1 : undefined"
      />
    </div>

    <h2 class="mb-2 text-sm font-semibold text-gray-900">Serie NDVI trimestral (Sentinel-2)</h2>
    <div class="mb-6 rounded-xl border border-gray-200 bg-white p-4">
      <LineChart :labels="ndviLabels()" :values="ndviValues()" />
    </div>

    <h2 class="mb-2 text-sm font-semibold text-gray-900">Notas sobre las fuentes de datos</h2>
    <ul class="list-disc space-y-1 pl-5 text-sm text-gray-600">
      <li v-for="(note, i) in analysis.dataset_notes" :key="i">{{ note }}</li>
    </ul>

    <p v-if="analysis.report_sha256" class="mt-4 break-all text-xs text-gray-400">
      SHA-256 del dossier: {{ analysis.report_sha256 }}
    </p>
  </div>
</template>
