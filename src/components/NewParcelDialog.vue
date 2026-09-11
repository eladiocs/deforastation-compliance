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
  (event: 'confirm', payload: { name: string; clientName: string; commodity: string }): void
  (event: 'cancel'): void
}>()

const name = ref('')
const clientName = ref('')
const commodity = ref('')

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      name.value = ''
      clientName.value = ''
      commodity.value = ''
    }
  }
)

function confirm(): void {
  if (!name.value.trim() || !commodity.value || props.isSaving) return
  emit('confirm', {
    name: name.value.trim(),
    clientName: clientName.value.trim(),
    commodity: commodity.value.trim(),
  })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/40 px-4">
    <div class="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
      <h2 class="text-lg font-semibold text-gray-900">Nueva parcela</h2>
      <div class="mt-4 space-y-3">
        <div>
          <label class="block text-sm font-medium text-gray-700">Nombre de la parcela <span class="text-red-500">*</span></label>
          <input
            v-model="name"
            type="text"
            :disabled="isSaving"
            class="mt-1 w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 disabled:bg-gray-100"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Cliente / importador</label>
          <input
            v-model="clientName"
            type="text"
            :disabled="isSaving"
            class="mt-1 w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 disabled:bg-gray-100"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Materia prima <span class="text-red-500">*</span></label>
          <select
            v-model="commodity"
            :disabled="isSaving"
            class="mt-1 w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 disabled:bg-gray-100"
          >
            <option value="">Selecciona…</option>
            <option value="cafe">Café</option>
            <option value="cacao">Cacao</option>
            <option value="soja">Soja</option>
            <option value="madera">Madera</option>
          </select>
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
          class="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:pointer-events-none disabled:opacity-50"
          :disabled="!name.trim() || !commodity || isSaving"
          @click="confirm"
        >
          {{ isSaving ? 'Guardando…' : 'Guardar parcela' }}
        </button>
      </div>
    </div>
  </div>
</template>
