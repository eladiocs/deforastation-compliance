<script setup lang="ts">
import Modal from './Modal.vue'

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
    dato: 'Parches de hábitat',
    fuente: 'ESA WorldCover (satélite, 2021) como fuente principal, complementado con OpenStreetMap (Overpass API, en vivo)',
    resolucion: 'WorldCover: píxel de 10 m, clasificado por tipo de cobertura. OSM: polígonos vectoriales exactos',
    metodo:
      'Se clasifican como hábitat las zonas de bosque, matorral, pastizal, humedal y manglar del mapa satelital. OpenStreetMap aporta el nombre real del lugar cuando existe, y añade zonas verdes pequeñas (p. ej. un jardín urbano) que el satélite no distingue del suelo construido. Un bosque grande y continuo no se representa como un único círculo: se reparte en varios parches distribuidos por su superficie. A cada parche se le asigna un radio según su área (entre 15 m y 300 m), hasta el número configurado.',
  },
  {
    dato: 'Coste de los corredores',
    fuente: 'ESA WorldCover (base) + OpenStreetMap (carreteras, cursos de agua, uso de suelo, en vivo vía Overpass API)',
    resolucion: 'Rejilla de resistencia de 25 m de celda (hasta 300×300 celdas), con la cobertura satelital de 10 m remuestreada a esa rejilla',
    metodo:
      'Ruta de menor coste (Dijkstra) entre parches situados dentro de la distancia de dispersión elegida. Cada celda parte del tipo de cobertura satelital (bosque/manglar fácil de cruzar, agua casi infranqueable) y luego se refuerza con las carreteras y cursos de agua de OpenStreetMap, que actúan como barrera aunque el satélite vea copa de árbol sobre ellos.',
  },
  {
    dato: 'Huella del proyecto',
    fuente: 'Dibujada a mano en el mapa, o subida como archivo GeoJSON por el usuario',
    resolucion: 'Según precisión del trazado',
    metodo:
      'Los parches que toca se marcan "perdidos". Además se añade a la rejilla de resistencia como una barrera casi infranqueable, así que cualquier corredor que sobreviva pero tenga que rodearla sale más caro.',
  },
]
</script>

<template>
  <Modal :open="open" @close="emit('close')">
    <template #header>
      <h2 class="text-lg font-semibold text-gray-900">Fuentes de datos y cálculos</h2>
      <p class="mt-1 text-sm text-gray-500">Qué se mide, con qué fuente, y qué significa realmente el resultado.</p>
    </template>

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
            <td class="py-2.5 pr-4 text-gray-600">{{ row.resolucion }}</td>
            <td class="py-2.5 pr-4 text-gray-600">{{ row.metodo }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4">
      <p class="text-sm text-amber-800">
        Los parches de hábitat y el coste de los corredores combinan una imagen satelital de 2021 (ESA WorldCover)
        con lo que la comunidad de OpenStreetMap ha cartografiado. Ambas fuentes pueden no reflejar el estado
        actual del terreno — por ejemplo, WorldCover puede confundir una plantación con bosque natural o no
        mostrar deforestación posterior a 2021, y OpenStreetMap puede tener carreteras o cursos de agua
        desactualizados. Un parche o corredor "sin cambios" no garantiza que no exista impacto real sobre el
        terreno — se recomienda validación de campo antes de usar este informe en un expediente formal.
      </p>
    </div>
  </Modal>
</template>
