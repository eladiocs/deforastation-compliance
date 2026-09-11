<script setup lang="ts">
withDefaults(
  defineProps<{
    open: boolean
    title: string
    message: string
    confirmLabel?: string
    cancelLabel?: string
  }>(),
  { confirmLabel: 'Confirmar', cancelLabel: 'Cancelar' }
)

const emit = defineEmits<{
  (event: 'confirm'): void
  (event: 'cancel'): void
}>()
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/40 px-4">
    <div class="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
      <h2 class="text-lg font-semibold text-gray-900">{{ title }}</h2>
      <p class="mt-2 text-sm text-gray-500">{{ message }}</p>
      <div class="mt-6 flex justify-end gap-2">
        <button
          class="rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          @click="emit('cancel')"
        >
          {{ cancelLabel }}
        </button>
        <button
          class="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700"
          @click="emit('confirm')"
        >
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>
