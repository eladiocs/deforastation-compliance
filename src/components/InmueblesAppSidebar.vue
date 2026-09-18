<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { HomeModernIcon, PlusIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import companyLogo from '@/assets/logo-empresa.png'
import { useInmueblesParcelsStore } from '@/stores/inmueblesParcels'
import BackToDashboardButton from '@/components/BackToDashboardButton.vue'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const route = useRoute()
const parcelsStore = useInmueblesParcelsStore()

onMounted(() => parcelsStore.fetchParcels())
watch(() => route.fullPath, () => emit('close'))
</script>

<template>
  <Transition
    enter-active-class="transition-opacity ease-linear duration-300"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity ease-linear duration-300"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="open"
      class="fixed inset-0 z-[1001] bg-gray-900/80 md:hidden"
      @click="emit('close')"
    />
  </Transition>
  <nav
    class="fixed inset-y-0 left-0 z-[1002] flex h-dvh w-64 shrink-0 -translate-x-full flex-col border-r border-gray-200 bg-white pb-[env(safe-area-inset-bottom)] pt-[env(safe-area-inset-top)] transition-transform duration-300 md:static md:z-auto md:translate-x-0"
    :class="{ 'translate-x-0': open }"
  >
    <Transition
      enter-active-class="ease-in-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="ease-in-out duration-300"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="absolute left-full top-0 flex w-16 justify-center pt-5 md:hidden">
        <button type="button" class="-m-2.5 p-2.5" aria-label="Cerrar menú" @click="emit('close')">
          <XMarkIcon class="h-6 w-6 text-white" aria-hidden="true" />
        </button>
      </div>
    </Transition>
    <BackToDashboardButton />
    <div class="border-b border-gray-100 px-5 pb-5 pt-2">
      <p class="text-3xl font-bold tracking-wide text-[#123a42]">Riesgo inmobiliario</p>
      <p class="mt-0.5 text-sm font-semibold text-[#5fb92c]">Riesgo de inundación por inmueble</p>
    </div>
    <div class="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
      <RouterLink
        to="/inmuebles"
        class="flex items-center gap-3 rounded-lg border-l-2 px-3 py-2.5 text-sm font-medium transition-colors hover:bg-[#f2f9ec] hover:text-[#123a42]"
        :class="
          route.path === '/inmuebles'
            ? 'border-[#5fb92c] bg-[#f2f9ec] font-semibold text-[#123a42]'
            : 'border-transparent text-gray-600'
        "
      >
        <PlusIcon class="h-5 w-5 shrink-0" />
        Nuevo inmueble
      </RouterLink>

      <p class="mt-4 px-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Inmuebles</p>

      <div v-if="parcelsStore.isLoading" class="flex flex-col gap-1.5 px-3 py-1">
        <div v-for="n in 3" :key="n" class="h-8 animate-pulse rounded-lg bg-gray-100" />
      </div>
      <p v-else-if="parcelsStore.error" class="px-3 py-1 text-xs text-red-600">{{ parcelsStore.error }}</p>
      <p v-else-if="parcelsStore.parcels.length === 0" class="px-3 py-1 text-xs text-gray-400">
        Todavía no hay inmuebles
      </p>
      <div v-else class="flex flex-col gap-0.5">
        <RouterLink
          v-for="p in parcelsStore.parcels"
          :key="p.id"
          :to="`/inmuebles/parcels/${p.id}`"
          class="flex min-w-0 items-center gap-3 rounded-lg border-l-2 px-3 py-2 text-sm font-medium transition-colors hover:bg-[#f2f9ec] hover:text-[#123a42]"
          :class="
            String(route.params.id) === String(p.id)
              ? 'border-[#5fb92c] bg-[#f2f9ec] font-semibold text-[#123a42]'
              : 'border-transparent text-gray-600'
          "
        >
          <HomeModernIcon class="h-4 w-4 shrink-0" />
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
