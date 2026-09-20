<script setup lang="ts">
import { api } from '@/api/inmueblesClient'
import type { Analysis } from '@/api/inmueblesTypes'
import RiskBadge from '@/components/RiskBadge.vue'

const props = defineProps<{
  analysis: Analysis
}>()

const severityClasses: Record<string, string> = {
  bajo: 'text-emerald-700',
  medio: 'text-amber-700',
  alto: 'text-red-700',
}
</script>

<template>
  <div>
    <div class="mb-4 flex justify-end">
      <a
        :href="api.reportUrl(analysis.id)"
        target="_blank"
        rel="noopener"
        class="rounded-md bg-[#5fb92c] px-4 py-2 text-sm font-medium text-white hover:bg-[#4ea023]"
      >
        Descargar PDF
      </a>
    </div>

    <div class="mb-6 rounded-xl border border-gray-200 bg-white p-4">
      <div class="flex items-center gap-3">
        <span class="text-2xl font-semibold text-gray-900">{{ analysis.risk_score.toFixed(0) }} / 100</span>
        <RiskBadge :label="analysis.risk_label" />
      </div>
    </div>

    <h2 class="mb-2 text-sm font-semibold text-gray-900">Factores considerados</h2>
    <div class="mb-6 overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table class="min-w-full divide-y divide-gray-200 text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-2 text-left font-medium text-gray-500">Factor</th>
            <th class="px-4 py-2 text-left font-medium text-gray-500">Valor</th>
            <th class="px-4 py-2 text-left font-medium text-gray-500">Severidad</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="f in analysis.risk_factors" :key="f.key">
            <td class="px-4 py-2 text-gray-900">{{ f.label }}</td>
            <td class="px-4 py-2 whitespace-nowrap text-gray-600">{{ f.value }} {{ f.unit }}</td>
            <td class="px-4 py-2 font-medium capitalize" :class="severityClasses[f.severity]">
              {{ f.severity }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <h2 class="mb-2 text-sm font-semibold text-gray-900">Notas sobre las fuentes de datos</h2>
    <ul class="list-disc space-y-1 pl-5 text-sm text-gray-600">
      <li v-for="(note, i) in analysis.dataset_notes" :key="i">{{ note }}</li>
    </ul>
  </div>
</template>
