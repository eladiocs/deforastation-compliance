import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'new-parcel', component: () => import('@/views/NewParcel.vue') },
    { path: '/parcels/new', redirect: '/' },
    { path: '/parcels/:id', name: 'parcel-detail', component: () => import('@/views/ParcelDetail.vue') },
  ],
})

export default router
