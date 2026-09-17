import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeDashboard.vue'),
      meta: { hideChrome: true },
    },
    {
      path: '/deforestacion',
      name: 'new-parcel',
      component: () => import('@/views/NewParcel.vue'),
      meta: { module: 'deforestacion' },
    },
    {
      path: '/deforestacion/parcels/:id',
      name: 'parcel-detail',
      component: () => import('@/views/ParcelDetail.vue'),
      meta: { module: 'deforestacion' },
    },
    {
      path: '/corredores',
      name: 'bio-new-parcel',
      component: () => import('@/views/BioNewParcel.vue'),
      meta: { module: 'corredores' },
    },
    {
      path: '/corredores/parcels/:id',
      name: 'bio-parcel-detail',
      component: () => import('@/views/BioParcelDetail.vue'),
      meta: { module: 'corredores' },
    },
  ],
})

export default router
