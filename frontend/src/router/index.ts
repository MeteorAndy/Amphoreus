import { createRouter, createWebHashHistory } from 'vue-router'
import WorldBuilderView from '../views/WorldBuilderView.vue'
import CharacterView from '../views/CharacterView.vue'
import PlotView from '../views/PlotView.vue'
import SceneView from '../views/SceneView.vue'
import WriterView from '../views/WriterView.vue'

const routes = [
  { path: '/', redirect: '/world' },
  { path: '/world', name: 'World', component: WorldBuilderView },
  { path: '/characters', name: 'Characters', component: CharacterView },
  { path: '/plot', name: 'Plot', component: PlotView },
  { path: '/scene', name: 'Scene', component: SceneView },
  { path: '/writer', name: 'Writer', component: WriterView },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
