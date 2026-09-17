<script setup lang="ts">
import { DISPERSAL_PRESETS } from '@/lib/dispersalPresets'
import type { ProjectMeta } from '@/composables/useImpactAnalysis'

const props = defineProps<{
  dispersalPresetId: string
  customDispersalDistance: number
  count: number
  projectMeta: ProjectMeta
  busy: boolean
}>()

const emit = defineEmits<{
  'update:dispersalPresetId': [value: string]
  'update:customDispersalDistance': [value: number]
  'update:count': [value: number]
  generateAnalysis: []
}>()

function updateMeta(field: keyof ProjectMeta, value: string) {
  props.projectMeta[field] = value
}
</script>

<template>
  <div class="space-y-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
    <div>
      <h2 class="text-sm font-semibold text-[#123a42]">Informe</h2>
      <div class="mt-2 space-y-2">
        <textarea
          :value="projectMeta.description"
          placeholder="Descripción breve"
          rows="2"
          class="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-[#5fb92c] focus:outline-none focus:ring-1 focus:ring-[#5fb92c]"
          @input="updateMeta('description', ($event.target as HTMLTextAreaElement).value)"
        />
        <input
          :value="projectMeta.preparedBy"
          type="text"
          placeholder="Elaborado por"
          class="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-[#5fb92c] focus:outline-none focus:ring-1 focus:ring-[#5fb92c]"
          @input="updateMeta('preparedBy', ($event.target as HTMLInputElement).value)"
        />
      </div>
    </div>

    <div class="border-t border-gray-100 pt-3">
      <label class="text-sm font-semibold text-[#123a42]">Especie objetivo / dispersión</label>
      <select
        :value="dispersalPresetId"
        :disabled="busy"
        class="mt-2 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
        @change="emit('update:dispersalPresetId', ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="preset in DISPERSAL_PRESETS" :key="preset.id" :value="preset.id">
          {{ preset.label }}
        </option>
      </select>
      <div v-if="dispersalPresetId === 'custom'" class="mt-2 flex items-center gap-2">
        <input
          type="range"
          min="40"
          max="1000"
          step="10"
          :value="customDispersalDistance"
          :disabled="busy"
          class="w-1/2 accent-[#5fb92c] disabled:cursor-not-allowed disabled:opacity-50"
          @input="emit('update:customDispersalDistance', Number(($event.target as HTMLInputElement).value))"
        />
        <span class="tabular-nums text-sm text-gray-500">{{ customDispersalDistance }} m</span>
      </div>
      <p class="mt-1 text-xs text-gray-500">
        Rango de movimiento estimado de la especie objetivo entre parches de hábitat.
      </p>
    </div>

    <div class="flex flex-wrap gap-2 border-t border-gray-100 pt-3">
      <button
        class="rounded-md bg-[#5fb92c] px-3 py-1.5 text-sm font-medium text-white hover:bg-[#4ea023] disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="busy"
        title="Vuelve a ejecutar el cálculo de corredores ecológicos"
        @click="emit('generateAnalysis')"
      >
        Generar análisis
      </button>
    </div>
  </div>
</template>
