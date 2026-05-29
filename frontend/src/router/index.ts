import { createRouter, createWebHashHistory } from 'vue-router'
import WorldBuilderView from '../views/WorldBuilderView.vue'
import CharacterView from '../views/CharacterView.vue'
import PlotView from '../views/PlotView.vue'
import SceneView from '../views/SceneView.vue'
import WriterView from '../views/WriterView.vue'
import PipelineView from '../views/PipelineView.vue'
import ProjectsView from '../views/ProjectsView.vue'
import InteractiveView from '../views/InteractiveView.vue'
import SandboxView from '../views/SandboxView.vue'

const routes = [
  { path: '/', redirect: '/projects' },
  { path: '/projects', name: 'Projects', component: ProjectsView },
  { path: '/pipeline', name: 'Pipeline', component: PipelineView },
  { path: '/interactive', name: 'Interactive', component: InteractiveView },
  { path: '/sandbox', name: 'Sandbox', component: SandboxView },
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

