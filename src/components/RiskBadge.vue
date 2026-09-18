<script setup lang="ts">
import { computed } from 'vue'

import type { RiskLabel } from '@/api/inmueblesTypes'

const props = defineProps<{ label: RiskLabel }>()

const labels: Record<RiskLabel, string> = {
  bajo: 'Riesgo bajo',
  medio: 'Riesgo medio',
  alto: 'Riesgo alto',
  muy_alto: 'Riesgo muy alto',
}

const classes: Record<RiskLabel, string> = {
  bajo: 'bg-emerald-100 text-emerald-800',
  medio: 'bg-amber-100 text-amber-800',
  alto: 'bg-red-100 text-red-800',
  muy_alto: 'bg-red-200 text-red-900',
}

const label = computed(() => labels[props.label])
const cls = computed(() => classes[props.label])
</script>

<template>
  <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" :class="cls">
    {{ label }}
  </span>
</template>
