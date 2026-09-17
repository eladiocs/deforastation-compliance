<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Parcel } from '@/types'

const props = withDefaults(
  defineProps<{ parcel: Parcel | null; isSaving?: boolean; saveError?: string | null }>(),
  { isSaving: false, saveError: null },
)
const emit = defineEmits<{ confirm: [payload: { name: string }]; cancel: [] }>()

const name = ref('')

watch(
  () => props.parcel,
  (parcel) => {
    if (parcel) name.value = parcel.name
  },
  { immediate: true },
)

function confirm(): void {
  if (!name.value.trim() || props.isSaving) return
  emit('confirm', { name: name.value.trim() })
}
</script>

<template>
  <div v-if="parcel" class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/40 px-4">
    <div class="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
      <h2 class="text-lg font-semibold text-[#123a42]">Editar parcela</h2>
      <div class="mt-4">
        <label class="block text-sm font-medium text-gray-700">
          Nombre de la parcela <span class="text-red-500">*</span>
        </label>
        <input
          v-model="name"
          type="text"
          :disabled="isSaving"
          class="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-[#5fb92c] focus:outline-none focus:ring-1 focus:ring-[#5fb92c] disabled:bg-gray-100"
          @keyup.enter="confirm"
        />
        <p v-if="saveError" class="mt-2 text-sm text-red-600">{{ saveError }}</p>
      </div>
      <div class="mt-6 flex justify-end gap-2">
        <button
          type="button"
          class="rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          @click="emit('cancel')"
        >
          Cancelar
        </button>
        <button
          type="button"
          class="rounded-md bg-[#5fb92c] px-3 py-2 text-sm font-medium text-white hover:bg-[#4ea023] disabled:pointer-events-none disabled:opacity-50"
          :disabled="!name.trim() || isSaving"
          @click="confirm"
        >
          {{ isSaving ? 'Guardando…' : 'Guardar cambios' }}
        </button>
      </div>
    </div>
  </div>
</template>
