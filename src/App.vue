<script setup lang="ts">
import { ref } from 'vue'
import { Bars3Icon, InformationCircleIcon } from '@heroicons/vue/24/outline'
import AppSidebar from '@/components/AppSidebar.vue'
import DataSourcesModal from '@/components/DataSourcesModal.vue'

const sidebarOpen = ref(false)
const dataSourcesOpen = ref(false)
</script>

<template>
  <div class="flex h-dvh bg-gray-50">
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-[1001] bg-black/40 md:hidden"
      @click="sidebarOpen = false"
    />
    <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />
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
        <p class="text-lg font-bold text-[#123a42]">Anti-deforestación</p>
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
          Procedencia de los datos y cálculos
        </button>
      </footer>
    </div>
    <DataSourcesModal :open="dataSourcesOpen" @close="dataSourcesOpen = false" />
  </div>
</template>
