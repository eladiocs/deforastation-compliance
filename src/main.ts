import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import './style.css'

import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// leaflet-draw's UMD build patches a global "L" rather than importing leaflet as
// an ES module — in the production bundle (two lazy-loaded map routes instead of
// one) that global lookup no longer resolves on its own, causing "L is not
// defined" at runtime. Exposing it explicitly here, before leaflet-draw loads,
// keeps it pointed at the same leaflet instance every component imports.
;(globalThis as unknown as { L: typeof L }).L = L

import 'leaflet-draw'

// Leaflet's default marker icon isn't imported directly — it's detected at
// runtime from the computed background-image of a CSS class in leaflet.css.
// With lazy-loaded map routes, the marker can be created before the browser
// finishes applying that dynamically-injected stylesheet, so the icon URL
// detection silently returns nothing and the marker disappears in production.
// Setting the URLs explicitly from imported assets removes that race entirely.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'

const app = createApp(App).use(createPinia()).use(router)

// Wait for the router to resolve the initial route before mounting, so App.vue's
// route.meta-based layout (sidebar vs. bare dashboard) is correct on first paint
// instead of flashing the sidebar layout for a frame.
router.isReady().then(() => app.mount('#app'))
