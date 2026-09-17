import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import './style.css'

import L from 'leaflet'

// leaflet-draw's UMD build patches a global "L" rather than importing leaflet as
// an ES module — in the production bundle (two lazy-loaded map routes instead of
// one) that global lookup no longer resolves on its own, causing "L is not
// defined" at runtime. Exposing it explicitly here, before leaflet-draw loads,
// keeps it pointed at the same leaflet instance every component imports.
;(globalThis as unknown as { L: typeof L }).L = L

import 'leaflet-draw'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'

const app = createApp(App).use(createPinia()).use(router)

// Wait for the router to resolve the initial route before mounting, so App.vue's
// route.meta-based layout (sidebar vs. bare dashboard) is correct on first paint
// instead of flashing the sidebar layout for a frame.
router.isReady().then(() => app.mount('#app'))
