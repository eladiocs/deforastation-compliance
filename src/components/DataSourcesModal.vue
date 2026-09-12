<script setup lang="ts">
import { XMarkIcon } from '@heroicons/vue/24/outline'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

interface SourceRow {
  dato: string
  fuente: string
  resolucion: string
  metodo: string
}

const SOURCES: SourceRow[] = [
  {
    dato: 'Pérdida de cobertura forestal',
    fuente: 'Hansen Global Forest Change (Universidad de Maryland), vía Google Earth Engine',
    resolucion: '30 m · anual, histórico desde 2001',
    metodo:
      'Se toma como bosque base todo píxel con cobertura de copa > umbral configurado (10% por defecto) en el año 2000. Se considera pérdida "tras el corte" la que el propio dataset atribuye a un año posterior a la fecha de corte configurada.',
  },
  {
    dato: 'Vigor de la vegetación (NDVI)',
    fuente: 'Satélite Sentinel-2 (Copernicus / ESA), vía Google Earth Engine',
    resolucion: '10 m · compuestos trimestrales',
    metodo:
      'Serie de apoyo visual para los meses que Hansen todavía no cubre (el dataset anual suele ir con 9-12 meses de retraso). No es una clasificación de pérdida por sí misma.',
  },
  {
    dato: 'Límites de la parcela',
    fuente: 'Dibujados a mano en el mapa, o subidos como archivo GeoJSON por el usuario',
    resolucion: 'Según precisión del trazado',
    metodo: 'No se contrasta contra ningún catastro oficial; la geometría es la que aporta quien crea la parcela.',
  },
]
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/40 px-4">
    <div class="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-xl bg-white shadow-xl">
      <div class="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-4">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">Fuentes de datos y cálculos</h2>
          <p class="mt-1 text-sm text-gray-500">Qué se mide, con qué fuente, y qué significa realmente el resultado.</p>
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
        <div class="overflow-x-auto">
          <table class="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr class="border-b border-gray-200 text-xs uppercase text-gray-500">
                <th class="py-2 pr-4">Dato / cálculo</th>
                <th class="py-2 pr-4">Fuente</th>
                <th class="py-2 pr-4">Resolución</th>
                <th class="py-2 pr-4">Método</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in SOURCES" :key="row.dato" class="border-b border-gray-100 align-top last:border-b-0">
                <td class="py-2.5 pr-4 font-medium text-gray-900">{{ row.dato }}</td>
                <td class="py-2.5 pr-4 text-gray-600">{{ row.fuente }}</td>
                <td class="py-2.5 pr-4 whitespace-nowrap text-gray-600">{{ row.resolucion }}</td>
                <td class="py-2.5 pr-4 text-gray-600">{{ row.metodo }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p class="mt-1.5 text-sm text-amber-800">
            El Reglamento europeo de deforestación (EUDR) usa la fecha de corte (31/12/2020 por defecto) como un
            punto de reinicio, no como una prohibición retroactiva: una parcela deforestada
            <strong>antes</strong> de esa fecha se considera "libre de deforestación" a efectos del reglamento,
            aunque históricamente fuera bosque. Esta herramienta solo detecta pérdida de cobertura forestal
            <strong>posterior</strong> al corte — un resultado "conforme" no certifica que la parcela nunca
            haya sido bosque, solo que no hay deforestación detectada después de esa fecha.
          </p>
          <p class="mt-1.5 text-sm text-amber-800">
            El EUDR exige además que la producción sea <strong>legal</strong> según la normativa del país de
            origen. Si la deforestación histórica (anterior al corte) fue ilegal en su momento, el producto
            podría seguir sin ser conforme por esa vía — pero esta app no lo puede verificar por satélite: haría
            falta contrastar catastro, permisos y titularidad de la tierra, datos que no maneja esta herramienta.
          </p>
        </div>
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
