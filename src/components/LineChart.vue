<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  labels: string[]
  values: (number | null)[]
  seriesLabel?: string
}>()

const width = 640
const height = 220
const padding = { top: 22, right: 10, bottom: 34, left: 40 }
const chartW = width - padding.left - padding.right
const chartH = height - padding.top - padding.bottom

const validValues = computed(() => props.values.filter((v): v is number => v !== null))
const minValue = computed(() => Math.min(0, ...validValues.value))
const maxValue = computed(() => Math.max(1, ...validValues.value))

const yTicks = computed(() => {
  const count = 4
  const range = maxValue.value - minValue.value || 1
  return Array.from({ length: count + 1 }, (_, i) => {
    const value = minValue.value + (range / count) * i
    return {
      value,
      y: padding.top + chartH - ((value - minValue.value) / range) * chartH,
    }
  })
})

function xFor(i: number) {
  return padding.left + (i / Math.max(1, props.values.length - 1)) * chartW
}
function yFor(v: number) {
  const range = maxValue.value - minValue.value || 1
  return padding.top + chartH - ((v - minValue.value) / range) * chartH
}

const points = computed(() =>
  props.values
    .map((v, i) => (v === null ? null : { x: xFor(i), y: yFor(v) }))
    .filter((p): p is { x: number; y: number } => p !== null),
)

const path = computed(() => points.value.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' '))
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" class="w-full max-h-64">
    <g v-for="(t, i) in yTicks" :key="'t' + i">
      <line :x1="padding.left" :y1="t.y" :x2="padding.left + chartW" :y2="t.y" stroke="#e5e7eb" stroke-width="1" />
      <text :x="padding.left - 6" :y="t.y + 3" font-size="9" text-anchor="end" fill="#6b7280">
        {{ t.value.toFixed(2) }}
      </text>
    </g>

    <g transform="translate(0, 0)">
      <line :x1="padding.left" :y1="8" :x2="padding.left + 16" :y2="8" stroke="#059669" stroke-width="2" />
      <circle :cx="padding.left + 8" :cy="8" r="2.5" fill="#059669" />
      <text :x="padding.left + 22" :y="11" font-size="9" fill="#6b7280">{{ seriesLabel ?? 'NDVI medio' }}</text>
    </g>

    <path :d="path" fill="none" stroke="#059669" stroke-width="2" />
    <circle v-for="(p, i) in points" :key="i" :cx="p.x" :cy="p.y" r="2.5" fill="#059669" />
    <text
      v-for="(label, i) in labels"
      v-show="i % Math.ceil(labels.length / 8 || 1) === 0"
      :key="'l' + i"
      :x="xFor(i)"
      :y="padding.top + chartH + 14"
      font-size="9"
      text-anchor="middle"
      fill="#6b7280"
    >
      {{ label }}
    </text>
  </svg>
</template>
