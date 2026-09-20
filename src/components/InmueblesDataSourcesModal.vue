<script setup lang="ts">
import Modal from '@/components/Modal.vue'

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
    dato: 'Altura sobre el drenaje más cercano (HAND)',
    fuente: 'MERIT Hydro v1.0.1 (banda "hnd"), vía Google Earth Engine',
    resolucion: '~90 m',
    metodo:
      'Es el factor que determina el riesgo por elevación: una medición hidrológica real (altura sobre la red de drenaje más cercana), evaluada en el propio punto, sin radio de análisis ni buffer. También descarta el riesgo por cercanía a un cauce o a agua permanente cuando el punto está a 20 m o más por encima del drenaje más cercano, para no penalizar ubicaciones elevadas sobre un valle o cauce cercano en horizontal pero inalcanzable por su inundación (p. ej. el casco antiguo de Teruel o el Alcázar de Toledo, ambos sobre promontorios).',
  },
  {
    dato: 'Elevación y pendiente del terreno (datos de referencia)',
    fuente: 'Copernicus DEM GLO-30 (ESA/Comisión Europea), vía Google Earth Engine',
    resolucion: '30 m',
    metodo:
      'Elevación y pendiente absolutas en el punto, mostradas como referencia. El riesgo por elevación lo determina HAND (fila anterior), no estos valores.',
  },
  {
    dato: 'Ocupación histórica de agua y distancia a agua permanente',
    fuente: 'JRC Global Surface Water v1.4 (Comisión Europea), vía Google Earth Engine',
    resolucion: '30 m · histórico 1984-2021',
    metodo:
      'Un pixel se considera "agua permanente" si históricamente estuvo ocupado por agua al menos el 50% del tiempo. La distancia se evalúa en el propio punto del inmueble (no como el mínimo dentro de un radio de búsqueda amplio, que puede reportar una distancia casi nula si un cuerpo de agua simplemente pasa dentro del radio). Se descarta cuando HAND indica que el punto está 20 m o más por encima del drenaje más cercano.',
  },
  {
    dato: 'Distancia a un cauce de drenaje',
    fuente: 'MERIT Hydro v1.0.1, vía Google Earth Engine',
    resolucion: '~90 m',
    metodo:
      'Se considera "cauce" cualquier punto con al menos 10 km² de cuenca aguas arriba (área de drenaje), derivado del terreno — no de si el satélite lo vio mojado alguna vez. Esto detecta barrancos y ramblas mediterráneos que están secos la mayor parte del año y solo llevan agua en episodios de lluvia torrencial (el mecanismo de la DANA de Valencia de 2024), que el dato de ocupación histórica de agua no puede ver. Igual que la distancia a agua permanente, se evalúa en el propio punto y se descarta cuando HAND indica 20 m o más de altura sobre el drenaje más cercano.',
  },
  {
    dato: 'Ubicación del inmueble',
    fuente: 'Marcado a mano en el mapa por el usuario, u obtenido por búsqueda de dirección/ciudad',
    resolucion: 'Según precisión del marcado',
    metodo:
      'No se contrasta contra ningún catastro oficial; el punto es el que aporta quien crea el inmueble. El riesgo se evalúa siempre sobre ese punto exacto, no sobre un área o buffer alrededor de él.',
  },
]
</script>

<template>
  <Modal :open="open" max-width-class="max-w-4xl" @close="emit('close')">
    <template #header>
      <h2 class="text-lg font-semibold text-gray-900">Fuentes de datos y cálculos</h2>
      <p class="mt-1 text-sm text-gray-500">Qué se mide, con qué fuente, y qué significa realmente el resultado.</p>
    </template>

    <div class="overflow-x-auto">
      <table class="w-full min-w-[720px] table-fixed text-left text-sm">
        <thead>
          <tr class="border-b border-gray-200 text-xs uppercase text-gray-500">
            <th class="w-[20%] py-2 pr-4">Dato / cálculo</th>
            <th class="w-[20%] py-2 pr-4">Fuente</th>
            <th class="w-[20%] py-2 pr-4">Resolución</th>
            <th class="w-[40%] py-2 pr-4">Método</th>
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
      <p class="mt-1.5 text-sm text-amber-800">
        Este score es una <strong>herramienta de apoyo</strong> basada en datasets globales de
        propósito general, no un estudio hidrológico-hidráulico formal. Complementa a las capas
        oficiales de zonas inundables aplicables en la jurisdicción del inmueble (por ejemplo, el
        <strong>SNCZI</strong> en España) detectando cauces y barrancos que estas capas, al basarse
        solo en cursos de agua formalmente estudiados, pueden no tener mapeados — pero no las
        sustituye: deben consultarse igualmente para cualquier trámite regulatorio, de seguro o de
        compraventa.
      </p>
    </div>
  </Modal>
</template>
