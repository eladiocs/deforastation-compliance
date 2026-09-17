<script setup lang="ts">
import { computed } from 'vue'
import type { ImpactAnalysisResult } from '@/types'

const props = defineProps<{ result: ImpactAnalysisResult }>()

type Status = 'no-impact' | 'moderate' | 'critical'

const status = computed<Status>(() => {
  if (props.result.patchesLost.length || props.result.corridorsLost.length) return 'critical'
  if (props.result.newlyIsolatedPatchIds.length) return 'moderate'
  return 'no-impact'
})

const labels: Record<Status, string> = {
  'no-impact': 'Sin impacto',
  moderate: 'Impacto moderado',
  critical: 'Impacto crítico',
}
const classes: Record<Status, string> = {
  'no-impact': 'bg-emerald-100 text-emerald-800',
  moderate: 'bg-amber-100 text-amber-800',
  critical: 'bg-red-100 text-red-800',
}
</script>

<template>
  <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" :class="classes[status]">
    {{ labels[status] }}
  </span>
</template>
