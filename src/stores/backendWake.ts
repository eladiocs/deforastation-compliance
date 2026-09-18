import { defineStore } from 'pinia'
import { reactive } from 'vue'

import { checkHealth as checkDeforestacionHealth } from '@/api/client'
import { checkHealth as checkInmueblesHealth } from '@/api/inmueblesClient'
import { checkHealth as checkCorredoresHealth } from '@/lib/api'

export type BackendModule = 'deforestacion' | 'corredores' | 'inmuebles'

const CHECKERS: Record<BackendModule, () => Promise<boolean>> = {
  deforestacion: checkDeforestacionHealth,
  corredores: checkCorredoresHealth,
  inmuebles: checkInmueblesHealth,
}

// Render's free tier sleeps the backend after 15 min idle and takes ~30-50s to
// wake on the next request. Poll /health until it responds instead of letting
// the user's first real action (e.g. drawing a polygon) fail silently. Give up
// after a hard cap so it never spins forever if the backend is genuinely down.
const POLL_INTERVAL_MS = 3_000
const GIVE_UP_AFTER_MS = 120_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export const useBackendWakeStore = defineStore('backendWake', () => {
  const checking = reactive<Record<BackendModule, boolean>>({
    deforestacion: false,
    corredores: false,
    inmuebles: false,
  })
  const ready = reactive<Record<BackendModule, boolean>>({
    deforestacion: false,
    corredores: false,
    inmuebles: false,
  })
  const failed = reactive<Record<BackendModule, boolean>>({
    deforestacion: false,
    corredores: false,
    inmuebles: false,
  })

  async function ensureAwake(moduleKey: BackendModule): Promise<void> {
    if (ready[moduleKey] || checking[moduleKey]) return
    checking[moduleKey] = true
    failed[moduleKey] = false

    const check = CHECKERS[moduleKey]
    const deadline = Date.now() + GIVE_UP_AFTER_MS
    while (Date.now() < deadline) {
      if (await check()) {
        ready[moduleKey] = true
        checking[moduleKey] = false
        return
      }
      await sleep(POLL_INTERVAL_MS)
    }

    checking[moduleKey] = false
    failed[moduleKey] = true
  }

  function retry(moduleKey: BackendModule): Promise<void> {
    failed[moduleKey] = false
    return ensureAwake(moduleKey)
  }

  return { checking, ready, failed, ensureAwake, retry }
})
