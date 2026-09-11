<script setup lang="ts">
import { InformationCircleIcon } from '@heroicons/vue/24/outline'

defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center"
  >
    <InformationCircleIcon class="h-8 w-8 text-gray-400" />
    <p class="font-medium text-gray-700">{{ title }}</p>
    <p v-if="description" class="text-sm text-gray-500">{{ description }}</p>
  </div>
</template>
