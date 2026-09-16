<script setup lang="ts">
import { XMarkIcon } from '@heroicons/vue/24/outline'

withDefaults(defineProps<{ open: boolean; maxWidthClass?: string }>(), {
  maxWidthClass: 'max-w-3xl',
})
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/40 px-4"
    @click.self="emit('close')"
  >
    <div class="flex max-h-[85vh] w-full flex-col rounded-xl bg-white shadow-xl" :class="maxWidthClass">
      <div class="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-4">
        <div class="min-w-0">
          <slot name="header" />
        </div>
        <button
          class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          aria-label="Cerrar"
          @click="emit('close')"
        >
          <XMarkIcon class="h-6 w-6" />
        </button>
      </div>
      <div class="overflow-y-auto px-6 py-4">
        <slot />
      </div>
      <div class="flex justify-end border-t border-gray-100 px-6 py-3">
        <button
          class="rounded-md bg-[#123a42] px-4 py-2 text-sm font-medium text-white hover:bg-[#0d2b31]"
          @click="emit('close')"
        >
          Cerrar
        </button>
      </div>
    </div>
  </div>
</template>
