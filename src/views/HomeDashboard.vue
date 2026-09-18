<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ShieldCheckIcon, GlobeAmericasIcon, HomeModernIcon } from '@heroicons/vue/24/outline'

const router = useRouter()

const CARDS = [
  {
    title: 'Anti-deforestación',
    description: 'Cumplimiento EUDR: análisis de deforestación por parcela.',
    icon: ShieldCheckIcon,
    to: '/deforestacion',
  },
  {
    title: 'Corredores biológicos',
    description: 'Impacto de proyectos sobre la conectividad ecológica.',
    icon: GlobeAmericasIcon,
    to: '/corredores',
  },
  {
    title: 'Riesgo inmobiliario',
    description: 'Riesgo de inundación por inmueble, a partir de su ubicación.',
    icon: HomeModernIcon,
    to: '/inmuebles',
  },
] as const
</script>

<template>
  <div class="flex min-h-dvh items-center justify-center bg-gray-50 px-4 py-12">
    <div class="w-full max-w-4xl">
      <h1 class="text-center text-2xl font-bold tracking-wide text-[#123a42] sm:text-3xl">
        Informes de impacto ambiental
      </h1>

      <div class="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <button
          v-for="card in CARDS"
          :key="card.to"
          type="button"
          class="group flex flex-col items-start gap-4 rounded-2xl border border-gray-200 bg-white p-8 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-[#5fb92c] hover:shadow-md"
          @click="router.push(card.to)"
        >
          <span class="rounded-xl bg-[#f2f9ec] p-3 text-[#123a42] group-hover:bg-[#123a42] group-hover:text-white">
            <component :is="card.icon" class="h-7 w-7" />
          </span>
          <div>
            <p class="text-lg font-semibold text-[#123a42]">{{ card.title }}</p>
            <p class="mt-1 text-sm text-gray-500">{{ card.description }}</p>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>
