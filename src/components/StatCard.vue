<script setup lang="ts">
type Accent = 'default' | 'warning' | 'danger'

withDefaults(
  defineProps<{
    label: string
    value: string | number
    accent?: Accent
  }>(),
  { accent: 'default' },
)

const ACCENT_CLASSES: Record<Accent, string> = {
  default: 'text-gray-900',
  warning: 'text-amber-600',
  danger: 'text-red-600',
}
</script>

<template>
  <div class="rounded-xl border border-gray-200 p-4">
    <p class="text-sm text-gray-500">{{ label }}</p>
    <p class="mt-1 text-2xl font-semibold" :class="ACCENT_CLASSES[accent]">{{ value }}</p>
  </div>
</template>
