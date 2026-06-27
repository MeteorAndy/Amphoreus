import { ref, watch } from 'vue'

const STORAGE_KEY = 'amphoreus-workbench'

const WORKBENCH_ROUTES = new Set([
  '/writer',
  '/world',
  '/characters',
  '/plot',
  '/scene',
  '/quality',
  '/interactive',
  '/pipeline',
  '/sandbox',
])

const DEFAULT_RIGHT_PANEL_WIDTH = 380
const MIN_RIGHT_PANEL_WIDTH = 280
const MAX_RIGHT_PANEL_WIDTH = 600

interface SavedState {
  rightPanelVisible?: boolean
  rightPanelWidth?: number
  sidebarCollapsed?: boolean
  userToggledPanel?: boolean
}

function loadState(): SavedState {
  if (typeof window === 'undefined') return {}
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return {}
}

function saveState(): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      rightPanelVisible: rightPanelVisible.value,
      rightPanelWidth: rightPanelWidth.value,
      sidebarCollapsed: sidebarCollapsed.value,
      userToggledPanel: userToggledPanel.value,
    }))
  } catch { /* ignore */ }
}

function getDefaultVisibleForPath(path: string): boolean {
  for (const route of WORKBENCH_ROUTES) {
    if (path.startsWith(route)) return true
  }
  return false
}

function getCurrentPath(): string {
  if (typeof window === 'undefined') return '/'
  return window.location.hash.replace('#', '') || '/'
}

const saved = loadState()

const rightPanelWidth = ref(Math.min(
  MAX_RIGHT_PANEL_WIDTH,
  Math.max(MIN_RIGHT_PANEL_WIDTH, saved.rightPanelWidth ?? DEFAULT_RIGHT_PANEL_WIDTH),
))
const sidebarCollapsed = ref(saved.sidebarCollapsed ?? false)
const userToggledPanel = ref(saved.userToggledPanel ?? false)

const initialVisible = saved.userToggledPanel
  ? (saved.rightPanelVisible ?? false)
  : getDefaultVisibleForPath(getCurrentPath())
const rightPanelVisible = ref(initialVisible)

watch([rightPanelWidth, sidebarCollapsed, userToggledPanel], saveState)
watch(rightPanelVisible, () => {
  if (userToggledPanel.value) saveState()
})

function toggleRightPanel(): void {
  rightPanelVisible.value = !rightPanelVisible.value
  userToggledPanel.value = true
}

function setRightPanelWidth(w: number): void {
  rightPanelWidth.value = Math.min(
    MAX_RIGHT_PANEL_WIDTH,
    Math.max(MIN_RIGHT_PANEL_WIDTH, w),
  )
}

function toggleSidebar(): void {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function setDefaultForRoute(path: string): void {
  if (userToggledPanel.value) return
  rightPanelVisible.value = getDefaultVisibleForPath(path)
}

export function useWorkbench() {
  return {
    rightPanelVisible,
    rightPanelWidth,
    sidebarCollapsed,
    toggleRightPanel,
    setRightPanelWidth,
    toggleSidebar,
    setDefaultForRoute,
    DEFAULT_RIGHT_PANEL_WIDTH,
    MIN_RIGHT_PANEL_WIDTH,
    MAX_RIGHT_PANEL_WIDTH,
  }
}
