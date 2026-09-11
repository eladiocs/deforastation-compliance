<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  labels: (string | number)[]
  values: number[]
  highlightFrom?: number
  unit?: string
}>()

const width = 640
const height = 220
const padding = { top: 22, right: 10, bottom: 28, left: 46 }
const chartW = width - padding.left - padding.right
const chartH = height - padding.top - padding.bottom

function niceMax(v: number) {
  if (v <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(v))
  const normalized = v / magnitude
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10
  return step * magnitude
}

const maxValue = computed(() => niceMax(Math.max(...props.values, 0)))
const barWidth = computed(() => chartW / props.values.length)

const yTicks = computed(() => {
  const count = 4
  return Array.from({ length: count + 1 }, (_, i) => {
    const value = (maxValue.value / count) * i
    return {
      value,
      y: padding.top + chartH - (value / maxValue.value) * chartH,
    }
  })
})

const bars = computed(() =>
  props.values.map((v, i) => {
    const barHeight = maxValue.value > 0 ? (v / maxValue.value) * chartH : 0
    return {
      x: padding.left + i * barWidth.value + barWidth.value * 0.15,
      y: padding.top + (chartH - barHeight),
      w: barWidth.value * 0.7,
      h: barHeight,
      highlighted: props.highlightFrom !== undefined && Number(props.labels[i]) >= props.highlightFrom,
      label: props.labels[i],
      value: v,
    }
  }),
)

function formatTick(v: number) {
  return v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2)
}
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" class="w-full max-h-64">
    <g v-for="(t, i) in yTicks" :key="'t' + i">
      <line :x1="padding.left" :y1="t.y" :x2="padding.left + chartW" :y2="t.y" stroke="#e5e7eb" stroke-width="1" />
      <text :x="padding.left - 6" :y="t.y + 3" font-size="9" text-anchor="end" fill="#6b7280">
        {{ formatTick(t.value) }}
      </text>
    </g>
    <text :x="padding.left" :y="14" font-size="9" fill="#6b7280">{{ unit ?? 'ha' }}</text>

    <g v-if="highlightFrom !== undefined">
      <rect :x="width - 260" y="6" width="9" height="9" fill="#9ca3af" rx="1.5" />
      <text :x="width - 247" y="14" font-size="9" fill="#6b7280">Antes del corte EUDR</text>
      <rect :x="width - 130" y="6" width="9" height="9" fill="#dc2626" rx="1.5" />
      <text :x="width - 117" y="14" font-size="9" fill="#6b7280">Después del corte</text>
    </g>

    <g v-for="(b, i) in bars" :key="i">
      <rect :x="b.x" :y="b.y" :width="b.w" :height="b.h" :fill="b.highlighted ? '#dc2626' : '#9ca3af'" rx="1.5" />
      <text
        v-if="b.value > 0"
        :x="b.x + b.w / 2"
        :y="b.y - 4"
        font-size="8"
        text-anchor="middle"
        fill="#4b5563"
      >
        {{ formatTick(b.value) }}
      </text>
      <text
        v-if="i % Math.ceil(bars.length / 12 || 1) === 0"
        :x="b.x + b.w / 2"
        :y="padding.top + chartH + 14"
        font-size="9"
        text-anchor="middle"
        fill="#6b7280"
      >
        {{ b.label }}
      </text>
    </g>
  </svg>
</template>
