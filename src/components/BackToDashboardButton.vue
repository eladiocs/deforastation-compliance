<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'
</script>

<template>
  <RouterLink
    to="/"
    class="flex items-center gap-1.5 px-5 pb-3 pt-4 text-xs font-medium text-gray-500 hover:text-[#123a42]"
  >
    <ArrowLeftIcon class="h-3.5 w-3.5 shrink-0" />
    Volver al dashboard
  </RouterLink>
</template>
