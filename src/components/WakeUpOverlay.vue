<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'

const props = defineProps<{ failed: boolean }>()
const emit = defineEmits<{ retry: [] }>()

const elapsedSeconds = ref(0)
let intervalId: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  intervalId = setInterval(() => {
    elapsedSeconds.value += 1
  }, 1000)
})

onBeforeUnmount(() => {
  if (intervalId) clearInterval(intervalId)
})

// Retrying starts a fresh polling window in the store (see backendWake.ts),
// so the visible counter needs to restart from 0 too instead of continuing
// from whatever it reached before the previous attempt gave up.
watch(
  () => props.failed,
  (failed, previousFailed) => {
    if (previousFailed && !failed) {
      elapsedSeconds.value = 0
    }
  },
)
</script>

<template>
  <div class="fixed inset-0 z-[3000] flex items-center justify-center bg-white px-4">
    <div class="flex max-w-sm flex-col items-center gap-3 text-center">
      <template v-if="!props.failed">
        <span
          class="block h-10 w-10 shrink-0 animate-spin rounded-full border-4 border-[#123a42] border-t-transparent"
        />
        <p class="text-base font-semibold text-[#123a42]">Preparando el servidor…</p>
        <p class="text-sm text-gray-600">
          El servidor estaba inactivo por falta de uso y se está reiniciando. Esto puede tardar
          hasta un minuto — no es necesario recargar la página.
        </p>
        <p class="text-xs text-gray-400">{{ elapsedSeconds }}s</p>
      </template>
      <template v-else>
        <p class="text-base font-semibold text-red-600">No se pudo conectar con el servidor</p>
        <p class="text-sm text-gray-600">Verifica tu conexión a internet e inténtalo de nuevo.</p>
        <button
          type="button"
          class="mt-1 flex items-center gap-1.5 rounded-lg bg-[#123a42] px-4 py-2 text-sm font-medium text-white hover:bg-[#0d2a30]"
          @click="emit('retry')"
        >
          <ArrowPathIcon class="h-4 w-4" />
          Reintentar
        </button>
      </template>
    </div>
  </div>
</template>
