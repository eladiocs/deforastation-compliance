<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { DocumentPlusIcon, MapIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import companyLogo from '@/assets/logo-empresa.png'
import { useParcelsStore } from '@/stores/parcels'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const route = useRoute()
const parcelsStore = useParcelsStore()

onMounted(() => {
  parcelsStore.fetchParcels()
})

watch(
  () => route.fullPath,
  () => emit('close'),
)
</script>

<template>
  <nav
    class="fixed inset-y-0 left-0 z-40 flex h-screen w-64 shrink-0 -translate-x-full flex-col border-r border-gray-200 bg-white transition-transform duration-200 md:static md:translate-x-0"
    :class="{ 'translate-x-0': open }"
  >
    <div class="flex items-start justify-between border-b border-gray-100 px-5 pb-5 pt-6">
      <div>
        <p class="text-3xl font-bold tracking-wide text-[#123a42]">Trazabosque</p>
        <p class="mt-0.5 text-base font-semibold text-[#5fb92c]">Cumplimiento EUDR</p>
      </div>
      <button
        type="button"
        class="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 md:hidden"
        @click="emit('close')"
      >
        <XMarkIcon class="h-5 w-5" />
      </button>
    </div>
    <div class="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
      <RouterLink
        to="/"
        class="flex items-center gap-3 rounded-lg border-l-2 px-3 py-2.5 text-sm font-medium transition-colors hover:bg-gray-50 hover:text-[#123a42]"
        :class="
          route.path === '/'
            ? 'border-[#5fb92c] bg-[#f2f9ec] font-semibold text-[#123a42]'
            : 'border-transparent text-gray-600'
        "
      >
        <DocumentPlusIcon class="h-5 w-5 shrink-0" />
        Nueva parcela
      </RouterLink>

      <p class="mt-4 px-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Parcelas</p>

      <div v-if="parcelsStore.isLoading" class="flex flex-col gap-1.5 px-3 py-1">
        <div v-for="n in 3" :key="n" class="h-8 animate-pulse rounded-lg bg-gray-100" />
      </div>
      <p v-else-if="parcelsStore.error" class="px-3 py-1 text-xs text-red-600">{{ parcelsStore.error }}</p>
      <p v-else-if="parcelsStore.parcels.length === 0" class="px-3 py-1 text-xs text-gray-400">
        Todavía no hay parcelas
      </p>
      <div v-else class="flex flex-col gap-0.5">
        <RouterLink
          v-for="p in parcelsStore.parcels"
          :key="p.id"
          :to="`/parcels/${p.id}`"
          class="flex min-w-0 items-center gap-3 rounded-lg border-l-2 px-3 py-2 text-sm font-medium transition-colors hover:bg-gray-50 hover:text-[#123a42]"
          :class="
            route.params.id === p.id
              ? 'border-[#5fb92c] bg-[#f2f9ec] font-semibold text-[#123a42]'
              : 'border-transparent text-gray-600'
          "
        >
          <MapIcon class="h-4 w-4 shrink-0" />
          <span class="truncate">{{ p.name }}</span>
        </RouterLink>
      </div>
    </div>
    <div class="mt-auto flex flex-col border-t border-gray-100 px-5 py-6">
      <p class="text-left text-[11px] italic tracking-wider text-gray-700">Desarrollado por:</p>
      <img :src="companyLogo" alt="Enviro Cost Solutions" class="mt-2 h-40 w-40" />
    </div>
  </nav>
</template>
