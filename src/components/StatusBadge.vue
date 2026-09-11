<script setup lang="ts">
import { computed } from 'vue'

import type { ComplianceStatus } from '@/api/types'

const props = defineProps<{ status: ComplianceStatus }>()

const labels: Record<ComplianceStatus, string> = {
  compliant: 'Conforme',
  non_compliant: 'No conforme',
  needs_review: 'Revisión manual',
}

const classes: Record<ComplianceStatus, string> = {
  compliant: 'bg-emerald-100 text-emerald-800',
  non_compliant: 'bg-red-100 text-red-800',
  needs_review: 'bg-amber-100 text-amber-800',
}

const label = computed(() => labels[props.status])
const cls = computed(() => classes[props.status])
</script>

<template>
  <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" :class="cls">
    {{ label }}
  </span>
</template>
