<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Bars3Icon, InformationCircleIcon } from '@heroicons/vue/24/outline'
import AppSidebar from '@/components/AppSidebar.vue'
import BioAppSidebar from '@/components/BioAppSidebar.vue'
import InmueblesAppSidebar from '@/components/InmueblesAppSidebar.vue'
import DataSourcesModal from '@/components/DataSourcesModal.vue'
import BioDataSourcesModal from '@/components/BioDataSourcesModal.vue'
import InmueblesDataSourcesModal from '@/components/InmueblesDataSourcesModal.vue'
import WakeUpOverlay from '@/components/WakeUpOverlay.vue'
import { useBackendWakeStore, type BackendModule } from '@/stores/backendWake'

const route = useRoute()
const wakeStore = useBackendWakeStore()

const sidebarOpen = ref(false)
const dataSourcesOpen = ref(false)

const hideChrome = computed(() => Boolean(route.meta.hideChrome))
const isCorredores = computed(() => route.meta.module === 'corredores')
const isInmuebles = computed(() => route.meta.module === 'inmuebles')

watch(hideChrome, (hidden) => {
  if (!hidden) sidebarOpen.value = false
})

const currentModule = computed<BackendModule | undefined>(() => {
  const moduleKey = route.meta.module
  return moduleKey === 'deforestacion' || moduleKey === 'corredores' || moduleKey === 'inmuebles'
    ? moduleKey
    : undefined
})

watch(
  currentModule,
  (moduleKey) => {
    if (moduleKey) wakeStore.ensureAwake(moduleKey)
  },
  { immediate: true },
)

const isWakingUp = computed(() => {
  const moduleKey = currentModule.value
  return moduleKey ? wakeStore.checking[moduleKey] || wakeStore.failed[moduleKey] : false
})
const wakeFailed = computed(() => {
  const moduleKey = currentModule.value
  return moduleKey ? wakeStore.failed[moduleKey] : false
})

function retryWake(): void {
  const moduleKey = currentModule.value
  if (moduleKey) wakeStore.retry(moduleKey)
}

const SidebarComponent = computed(() => {
  if (isCorredores.value) return BioAppSidebar
  if (isInmuebles.value) return InmueblesAppSidebar
  return AppSidebar
})
const DataSourcesComponent = computed(() => {
  if (isCorredores.value) return BioDataSourcesModal
  if (isInmuebles.value) return InmueblesDataSourcesModal
  return DataSourcesModal
})
const headerTitle = computed(() => {
  if (isCorredores.value) return 'BioConnect'
  if (isInmuebles.value) return 'Riesgo inmobiliario'
  return 'Anti-deforestación'
})
const dataSourcesLabel = computed(() =>
  isCorredores.value || isInmuebles.value ? 'Fuentes de datos y cálculos' : 'Procedencia de los datos y cálculos',
)
</script>

<template>
  <WakeUpOverlay v-if="isWakingUp" :failed="wakeFailed" @retry="retryWake" />

  <RouterView v-else-if="hideChrome" />

  <div v-else class="flex h-dvh bg-gray-50">
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-[1001] bg-black/40 md:hidden"
      @click="sidebarOpen = false"
    />
    <component :is="SidebarComponent" :open="sidebarOpen" @close="sidebarOpen = false" />
    <div class="flex min-w-0 flex-1 flex-col">
      <header
        class="flex shrink-0 items-center gap-3 border-b border-gray-200 bg-white px-4 py-3 pt-[max(0.75rem,env(safe-area-inset-top))] md:hidden"
      >
        <button
          type="button"
          class="rounded-md p-1.5 text-gray-500 hover:bg-gray-100"
          @click="sidebarOpen = true"
        >
          <Bars3Icon class="h-6 w-6" />
        </button>
        <p class="text-lg font-bold text-[#123a42]">{{ headerTitle }}</p>
      </header>
      <main class="flex-1 overflow-y-auto p-4 sm:p-6">
        <RouterView :key="$route.fullPath" />
      </main>
      <footer
        class="flex shrink-0 items-center justify-center px-4 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2"
      >
        <button
          class="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-[#123a42]"
          @click="dataSourcesOpen = true"
        >
          <InformationCircleIcon class="h-4 w-4" />
          {{ dataSourcesLabel }}
        </button>
      </footer>
    </div>
    <component :is="DataSourcesComponent" :open="dataSourcesOpen" @close="dataSourcesOpen = false" />
  </div>
</template>
