<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import FootprintMap from '@/components/FootprintMap.vue'
import BioNewParcelDialog from '@/components/BioNewParcelDialog.vue'
import { useBioParcelsStore } from '@/stores/bioParcels'

const center: [number, number] = [40.4168, -3.7038] // Madrid
const zoom = 13

const router = useRouter()
const parcelsStore = useBioParcelsStore()
const footprintMapRef = ref<InstanceType<typeof FootprintMap> | null>(null)

const pendingFootprint = ref<{ lat: number; lng: number }[]>([])
const isDialogOpen = ref(false)
const submitting = ref(false)
const saveError = ref<string | null>(null)
const uploadedFileName = ref<string | null>(null)

function handleFootprintDefined(polygon: { lat: number; lng: number }[]) {
  pendingFootprint.value = polygon
  saveError.value = null
  isDialogOpen.value = true
}

function handleFileUploaded(name: string) {
  uploadedFileName.value = name
}

async function handleConfirm({ name }: { name: string }) {
  submitting.value = true
  saveError.value = null
  try {
    const parcel = await parcelsStore.createParcel(name, pendingFootprint.value)
    isDialogOpen.value = false
    router.push(`/corredores/parcels/${parcel.id}`)
  } catch {
    saveError.value = 'No se pudo crear la parcela. Inténtalo de nuevo.'
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  isDialogOpen.value = false
  pendingFootprint.value = []
  uploadedFileName.value = null
  footprintMapRef.value?.clearDrawing()
}
</script>

<template>
  <div class="space-y-3">
    <div>
      <h1 class="text-lg font-semibold text-[#123a42]">Nueva parcela</h1>
      <p class="text-sm text-gray-500">
        <button
          type="button"
          class="cursor-pointer font-medium text-gray-700 underline decoration-dotted underline-offset-2 hover:text-[#123a42]"
          @click="footprintMapRef?.triggerFileUpload()"
        >
          Sube un archivo geojson
        </button>
        o dibuja un polígono: pulsa el icono de polígono, marca cada vértice con clic y cierra la forma haciendo clic en el primer punto o pulsando "Finish".
        <span v-if="uploadedFileName" class="ml-1 text-xs text-gray-400">({{ uploadedFileName }})</span>
      </p>
    </div>

    <FootprintMap
      ref="footprintMapRef"
      :patches="[]"
      :patches-lost-ids="new Set()"
      :patches-isolated-ids="new Set()"
      :edges="[]"
      :edge-status="new Map()"
      :footprint="[]"
      :center="center"
      :zoom="zoom"
      @footprint-defined="handleFootprintDefined"
      @file-uploaded="handleFileUploaded"
    />

    <BioNewParcelDialog
      :open="isDialogOpen"
      :is-saving="submitting"
      :save-error="saveError"
      @confirm="handleConfirm"
      @cancel="handleCancel"
    />
  </div>
</template>
