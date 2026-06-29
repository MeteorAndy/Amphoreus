<script setup lang="ts">
import { type Component, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  FolderOpen, Zap, Sparkles, Globe,
  Users, ListTree, Drama, PenTool, ShieldCheck, Settings,
  Orbit, PanelLeftClose, MessageSquare, ChevronRight, Compass, Download,
} from 'lucide-vue-next'
import { useI18n } from '../i18n'
import { useWorkbench } from '../composables/useWorkbench'
import PanelResizeHandle from './PanelResizeHandle.vue'
import ToastContainer from './ToastContainer.vue'

const { t, setLang, currentLang } = useI18n()
const {
  rightPanelVisible,
  rightPanelWidth,
  toggleRightPanel,
  setRightPanelWidth,
  DEFAULT_RIGHT_PANEL_WIDTH,
  setDefaultForRoute,
} = useWorkbench()
const route = useRoute()
const router = useRouter()

interface NavItem {
  labelKey: string
  path: string
  icon: Component
}

interface NavGroup {
  labelKey: string
  items: NavItem[]
}

const navGroups: NavGroup[] = [
  {
    labelKey: 'nav.group_workflows',
    items: [
      { labelKey: 'nav.projects', path: '/projects', icon: Compass },
      { labelKey: 'nav.pipeline', path: '/pipeline', icon: Zap },
      { labelKey: 'nav.interactive', path: '/interactive', icon: Sparkles },
    ],
  },
  {
    labelKey: 'nav.group_workbench',
    items: [
      { labelKey: 'nav.world', path: '/world', icon: Globe },
      { labelKey: 'nav.characters', path: '/characters', icon: Users },
      { labelKey: 'nav.plot', path: '/plot', icon: ListTree },
      { labelKey: 'nav.scene', path: '/scene', icon: Drama },
      { labelKey: 'nav.writer', path: '/writer', icon: PenTool },
      { labelKey: 'nav.quality', path: '/quality', icon: ShieldCheck },
    ],
  },
]

function isActive(path: string): boolean {
  return route.path.startsWith(path)
}

function navigate(path: string): void {
  router.push(path)
}

function toggleLang(): void {
  setLang(currentLang.value === 'zh' ? 'en' : 'zh')
}

function handleResize(delta: number): void {
  setRightPanelWidth(rightPanelWidth.value + delta)
}

function resetPanelWidth(): void {
  setRightPanelWidth(DEFAULT_RIGHT_PANEL_WIDTH)
}

function expandPanel(): void {
  if (!rightPanelVisible.value) {
    toggleRightPanel()
  }
}

watch(
  () => route.path,
  (path) => {
    setDefaultForRoute(path)
  },
  { immediate: true },
)
</script>

<template>
  <div class="app-layout flex h-screen overflow-hidden">
    <aside class="sidebar flex flex-col flex-shrink-0" style="width:260px;">
      <div class="sidebar__inner flex flex-col h-full">
        <div class="brand-area px-4 pt-5 pb-3">
          <div class="brand-content flex items-center gap-3">
            <div class="brand-icon relative">
              <div class="brand-icon-glow"></div>
              <div class="brand-icon-inner w-10 h-10 rounded-xl flex items-center justify-center relative overflow-hidden">
                <Orbit :size="20" class="text-[#0b0d1a] relative z-10" :stroke-width="2.5" />
              </div>
            </div>
            <div class="brand-text min-w-0 flex-1">
              <div class="brand-name text-gold-gradient font-bold leading-tight tracking-wider" style="font-size:1.15rem;">
                AMPHOREUS
              </div>
              <div class="brand-subtitle text-[10px] tracking-[0.2em] uppercase text-[#6b6780] mt-0.5">
                Story Engine
              </div>
            </div>
          </div>
        </div>

        <div class="px-4 pb-2">
          <hr class="divider-hsr my-2" style="margin:0.5rem 0;" />
        </div>

        <nav class="nav-area flex-1 overflow-y-auto px-3 pb-2">
          <template v-for="(group, groupIndex) in navGroups" :key="group.labelKey">
            <div class="nav-group mb-4">
              <div class="nav-group-label px-3 py-1.5 text-[10px] tracking-[0.15em] uppercase font-semibold text-[#6b6780] flex items-center gap-2">
                <span class="w-1 h-1 rounded-full bg-[#d4a843]/40"></span>
                {{ t(group.labelKey) }}
              </div>
              <div class="nav-items mt-0.5 flex flex-col gap-0.5">
                <button
                  v-for="item in group.items"
                  :key="item.path"
                  @click="navigate(item.path)"
                  class="sidebar-nav-item w-full text-left"
                  :class="{ active: isActive(item.path) }"
                >
                  <component
                    :is="item.icon"
                    :size="16"
                    :stroke-width="isActive(item.path) ? 2 : 1.5"
                    class="flex-shrink-0"
                  />
                  <span class="nav-text leading-tight">{{ t(item.labelKey) }}</span>
                  <ChevronRight v-if="isActive(item.path)" :size="12" class="ml-auto opacity-60" />
                </button>
              </div>
            </div>
          </template>
        </nav>

        <div class="control-area px-3 pb-4">
          <hr class="divider-hsr" />
          <div class="control-buttons flex items-center gap-2 mt-3">
            <button
              @click="toggleRightPanel"
              class="control-btn flex-1 flex items-center justify-center gap-1.5"
              :class="{ 'control-btn--active': rightPanelVisible }"
              :title="rightPanelVisible ? '折叠AI面板' : '展开AI面板'"
            >
              <MessageSquare :size="14" :stroke-width="1.5" />
              <span class="text-xs">AI</span>
            </button>
            <button
              @click="() => router.push('/projects')"
              class="control-btn"
              title="项目"
            >
              <FolderOpen :size="14" :stroke-width="1.5" />
            </button>
            <button
              @click="toggleLang"
              class="control-btn lang-btn flex items-center justify-center"
              :title="t('lang.switch')"
            >
              {{ currentLang === 'zh' ? 'EN' : '中' }}
            </button>
          </div>
        </div>
      </div>
    </aside>

    <main class="main-content flex-1 min-w-0 overflow-hidden flex flex-col">
      <div
        class="main-inner flex-1 min-h-0 flex flex-col"
        :class="rightPanelVisible
          ? 'p-4'
          : 'max-w-7xl mx-auto px-6 py-4 overflow-y-auto'"
      >
        <slot />
      </div>
    </main>

    <template v-if="rightPanelVisible">
      <PanelResizeHandle @resize="handleResize" @reset="resetPanelWidth" />
      <aside
        class="right-panel flex flex-col flex-shrink-0"
        :style="{ width: `${rightPanelWidth}px` }"
      >
        <div class="right-panel__inner flex flex-col h-full">
          <div class="right-panel-header flex items-center justify-between px-4 py-3">
            <div class="flex items-center gap-2">
              <div class="w-6 h-6 rounded-md flex items-center justify-center bg-[#d4a843]/15 border border-[#d4a843]/30">
                <MessageSquare :size="13" :stroke-width="1.5" class="text-[#d4a843]" />
              </div>
              <span class="text-sm font-semibold tracking-wide text-[#e8e6f0]">AI 助手</span>
            </div>
            <button
              @click="toggleRightPanel"
              class="panel-collapse-btn"
              title="折叠面板"
            >
              <PanelLeftClose :size="14" :stroke-width="1.5" />
            </button>
          </div>
          <div class="px-4"><hr class="divider-hsr" style="margin:0;" /></div>
          <div class="right-panel-content flex-1 overflow-hidden">
            <slot name="right-panel" />
          </div>
        </div>
      </aside>
    </template>

    <div v-else class="right-panel-edge" @click="expandPanel" title="展开AI面板" />

    <ToastContainer />
  </div>
</template>

<style scoped>
.app-layout {
  position: relative;
}

.sidebar {
  background: rgba(15, 18, 40, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid rgba(212, 168, 67, 0.1);
  position: relative;
}

.sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(212, 168, 67, 0.2) 20%,
    rgba(212, 168, 67, 0.1) 50%,
    rgba(212, 168, 67, 0.2) 80%,
    transparent 100%
  );
  pointer-events: none;
}

.sidebar__inner {
  position: relative;
  z-index: 1;
}

.brand-icon {
  position: relative;
}

.brand-icon-glow {
  position: absolute;
  inset: -4px;
  background: radial-gradient(circle, rgba(212, 168, 67, 0.3) 0%, transparent 70%);
  filter: blur(8px);
  opacity: 0.6;
  animation: brandPulse 3s ease-in-out infinite;
}

@keyframes brandPulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.1); }
}

.brand-icon-inner {
  background: linear-gradient(135deg, #d4a843, #f0d078, #d4a843);
  box-shadow: 0 0 16px rgba(212, 168, 67, 0.3), 0 2px 8px rgba(0,0,0,0.3);
  position: relative;
}

.brand-icon-inner::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.3) 0%, transparent 50%);
  border-radius: inherit;
}

.brand-name {
  font-size: 1.15rem;
}

.nav-area::-webkit-scrollbar {
  width: 4px;
}

.nav-area::-webkit-scrollbar-track {
  background: transparent;
}

.nav-area::-webkit-scrollbar-thumb {
  background: rgba(212, 168, 67, 0.15);
  border-radius: 3px;
}

.nav-area::-webkit-scrollbar-thumb:hover {
  background: rgba(212, 168, 67, 0.3);
}

.control-btn {
  padding: 0.4rem 0.625rem;
  border-radius: 8px;
  font-size: 0.6875rem;
  font-weight: 500;
  color: #a09cb8;
  background: rgba(20, 24, 50, 0.6);
  border: 1px solid rgba(100, 95, 128, 0.15);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.control-btn:hover {
  background: rgba(30, 35, 70, 0.7);
  color: #e8e6f0;
  border-color: rgba(212, 168, 67, 0.2);
}

.control-btn:active {
  transform: scale(0.96);
}

.control-btn--active {
  color: #d4a843;
  border-color: rgba(212, 168, 67, 0.3);
  background: rgba(212, 168, 67, 0.1);
  box-shadow: 0 0 12px rgba(212, 168, 67, 0.1);
}

.lang-btn {
  min-width: 36px;
  font-weight: 600;
}

.main-content {
  animation: mainFadeIn 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
}

@keyframes mainFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.right-panel {
  background: rgba(15, 18, 40, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-left: 1px solid rgba(212, 168, 67, 0.1);
  position: relative;
  overflow: hidden;
}

.right-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(212, 168, 67, 0.2) 20%,
    rgba(212, 168, 67, 0.1) 50%,
    rgba(212, 168, 67, 0.2) 80%,
    transparent 100%
  );
  pointer-events: none;
}

.right-panel__inner {
  position: relative;
  z-index: 1;
}

.panel-collapse-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #a09cb8;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.panel-collapse-btn:hover {
  background: rgba(30, 35, 70, 0.5);
  color: #e8e6f0;
  border-color: rgba(100, 95, 128, 0.2);
}

.right-panel-edge {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 3px;
  z-index: 20;
  cursor: pointer;
  background: transparent;
  transition: all 0.2s;
}

.right-panel-edge:hover {
  background: linear-gradient(180deg,
    transparent 0%,
    rgba(212, 168, 67, 0.3) 20%,
    rgba(212, 168, 67, 0.5) 50%,
    rgba(212, 168, 67, 0.3) 80%,
    transparent 100%
  );
  width: 4px;
}

@media (prefers-reduced-motion: reduce) {
  .main-content,
  .brand-icon-glow {
    animation: none !important;
  }
}
</style>
