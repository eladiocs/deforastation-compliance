import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import './style.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'

const app = createApp(App).use(createPinia()).use(router)

// Wait for the router to resolve the initial route before mounting, so App.vue's
// route.meta-based layout (sidebar vs. bare dashboard) is correct on first paint
// instead of flashing the sidebar layout for a frame.
router.isReady().then(() => app.mount('#app'))
