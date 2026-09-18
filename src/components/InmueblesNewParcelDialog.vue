<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    isSaving?: boolean
    saveError?: string | null
  }>(),
  {
    isSaving: false,
    saveError: null,
  }
)

const emit = defineEmits<{
  (event: 'confirm', payload: { name: string; address: string }): void
  (event: 'cancel'): void
}>()

const name = ref('')
const address = ref('')

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      name.value = ''
      address.value = ''
    }
  }
)

function confirm(): void {
  if (!name.value.trim() || props.isSaving) return
  emit('confirm', {
    name: name.value.trim(),
    address: address.value.trim(),
  })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/40 px-4">
    <div class="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
      <h2 class="text-lg font-semibold text-gray-900">Nuevo inmueble</h2>
      <div class="mt-4 space-y-3">
        <div>
          <label class="block text-sm font-medium text-gray-700">Nombre <span class="text-red-500">*</span></label>
          <input
            v-model="name"
            type="text"
            :disabled="isSaving"
            class="mt-1 w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 disabled:bg-gray-100"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Dirección</label>
          <input
            v-model="address"
            type="text"
            :disabled="isSaving"
            class="mt-1 w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 disabled:bg-gray-100"
          />
        </div>
        <p v-if="saveError" class="text-sm text-red-600">
          {{ saveError }}
        </p>
      </div>
      <div class="mt-6 flex justify-end gap-2">
        <button
          class="rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          @click="emit('cancel')"
        >
          Cancelar
        </button>
        <button
          class="rounded-md bg-[#5fb92c] px-3 py-2 text-sm font-medium text-white hover:bg-[#4ea023] disabled:pointer-events-none disabled:opacity-50"
          :disabled="!name.trim() || isSaving"
          @click="confirm"
        >
          {{ isSaving ? 'Guardando…' : 'Guardar inmueble' }}
        </button>
      </div>
    </div>
  </div>
</template>
