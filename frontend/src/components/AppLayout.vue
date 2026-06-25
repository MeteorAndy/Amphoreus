<script setup lang="ts">
import { type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  FolderOpen, Zap, Sparkles, Globe,
  Users, ListTree, Drama, PenTool, ShieldCheck, Sun, Moon,
  BookOpen,
} from 'lucide-vue-next'
import { useI18n } from '../i18n'
import { useTheme } from '../composables/useTheme'
import ToastContainer from './ToastContainer.vue'

const { t, setLang, currentLang } = useI18n()
const { theme, toggle: toggleTheme } = useTheme()
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
      { labelKey: 'nav.projects', path: '/projects', icon: FolderOpen },
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
</script>

<template>
  <div class="app-layout flex h-screen overflow-hidden bg-ink-bg">
    <aside class="sidebar flex flex-col w-56 flex-shrink-0">
      <div class="sidebar__inner flex flex-col h-full">
        <div class="brand-area">
          <div class="brand-content flex items-center gap-3 px-4 py-4">
            <div class="seal-wrapper relative flex-shrink-0">
              <div class="seal-glow-layer absolute inset-0 rounded-seal"></div>
              <div class="seal w-9 h-9 rounded-seal flex items-center justify-center relative">
                <div class="seal-texture"></div>
                <BookOpen :size="17" class="text-white relative z-10" :stroke-width="2" />
              </div>
            </div>
            <div class="brand-text min-w-0 flex-1">
              <div class="brand-name font-display font-semibold text-parchment-bright leading-tight truncate">
                Amphoreus
              </div>
              <div class="brand-subtitle leading-tight">{{ t('app.title') }}</div>
            </div>
          </div>
          <div class="ornament-divider px-4">
            <div class="ornament-line"></div>
            <div class="ornament-dot"></div>
            <div class="ornament-line"></div>
          </div>
        </div>

        <nav class="nav-area flex-1 overflow-y-auto py-4 px-3">
          <template v-for="(group, groupIndex) in navGroups" :key="group.labelKey">
            <div class="nav-group" :style="{ animationDelay: `${groupIndex * 80}ms` }">
              <div class="nav-group-label">
                <span class="label-dot"></span>
                <span class="label-text">{{ t(group.labelKey) }}</span>
              </div>
              <div class="nav-items mt-1">
                <button
                  v-for="(item, itemIndex) in group.items"
                  :key="item.path"
                  @click="navigate(item.path)"
                  class="nav-item group w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all relative"
                  :class="{ 'nav-item--active': isActive(item.path) }"
                  :style="{ animationDelay: `${(groupIndex * 3 + itemIndex + 1) * 60}ms` }"
                >
                  <span class="nav-indicator absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r-full transition-all"></span>
                  <component 
                    :is="item.icon" 
                    :size="16" 
                    :stroke-width="isActive(item.path) ? 2 : 1.5" 
                    class="nav-icon flex-shrink-0 transition-all"
                  />
                  <span class="nav-text font-medium leading-tight">{{ t(item.labelKey) }}</span>
                </button>
              </div>
            </div>
          </template>
        </nav>

        <div class="control-area px-3 py-3">
          <div class="control-divider mb-3">
            <div class="divider-line"></div>
          </div>
          <div class="control-buttons flex items-center gap-2">
            <button
              @click="toggleTheme"
              class="control-btn flex-1 flex items-center justify-center gap-1.5"
              :title="theme === 'ink' ? t('theme.paper') : t('theme.ink')"
            >
              <component :is="theme === 'ink' ? Sun : Moon" :size="14" :stroke-width="1.5" />
              <span>{{ theme === 'ink' ? (currentLang === 'zh' ? '纸色' : 'Paper') : (currentLang === 'zh' ? '墨色' : 'Ink') }}</span>
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

    <main class="main-content flex-1 overflow-y-auto">
      <div class="main-inner max-w-7xl mx-auto px-8 py-6">
        <slot />
      </div>
    </main>

    <ToastContainer />
  </div>
</template>

<style scoped>
.app-layout {
  position: relative;
}

.sidebar {
  background: var(--color-ink-panel);
  background-image: 
    linear-gradient(180deg, rgba(237, 228, 211, 0.02) 0%, transparent 20%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='paper'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23paper)' opacity='0.025'/%3E%3C/svg%3E");
  border-right: 1px solid transparent;
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
    var(--color-chop-border) 15%,
    var(--color-ink-edge) 50%,
    var(--color-chop-border) 85%,
    transparent 100%
  );
  pointer-events: none;
}

.sidebar__inner {
  position: relative;
  z-index: 1;
}

.brand-area {
  position: relative;
}

.brand-content {
  position: relative;
}

.seal-wrapper {
  width: 36px;
  height: 36px;
}

.seal-glow-layer {
  background: var(--gradient-chop-glow);
  filter: blur(8px);
  opacity: 0.8;
  animation: sealPulse 3s ease-in-out infinite;
}

.seal {
  background: var(--gradient-chop-seal);
  box-shadow: 
    0 2px 8px rgba(200, 66, 59, 0.4),
    0 0 20px rgba(200, 66, 59, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.25),
    inset 0 -1px 0 rgba(0, 0, 0, 0.15);
  position: relative;
  overflow: hidden;
}

.seal::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: 
    radial-gradient(ellipse at 20% 30%, rgba(255, 255, 255, 0.15) 0%, transparent 40%),
    radial-gradient(ellipse at 80% 70%, rgba(0, 0, 0, 0.12) 0%, transparent 40%);
  z-index: 1;
}

.seal::after {
  content: '';
  position: absolute;
  inset: 2px;
  border-radius: inherit;
  border: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 2;
}

.seal-texture {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  opacity: 0.3;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='36' height='36'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='1.2' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.4'/%3E%3C/svg%3E");
  z-index: 0;
}

@keyframes sealPulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 0.9; transform: scale(1.05); }
}

.brand-name {
  font-size: 0.9375rem;
  letter-spacing: 0.04em;
}

.brand-subtitle {
  font-size: 0.6rem;
  color: var(--color-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-top: 2px;
}

.ornament-divider {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-bottom: 4px;
}

.ornament-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-ink-edge), transparent);
}

.ornament-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-chop);
  opacity: 0.7;
  box-shadow: 0 0 6px var(--color-chop-glow);
}

.nav-area::-webkit-scrollbar {
  width: 4px;
}

.nav-area::-webkit-scrollbar-track {
  background: transparent;
}

.nav-area::-webkit-scrollbar-thumb {
  background: var(--color-ink-edge);
  border-radius: var(--radius-seal);
}

.nav-area::-webkit-scrollbar-thumb:hover {
  background: var(--color-muted-soft);
}

.nav-group {
  margin-bottom: var(--space-element);
  animation: navSlideIn 0.4s var(--ease-seal) both;
  opacity: 0;
  transform: translateX(-8px);
}

@keyframes navSlideIn {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.nav-group-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: var(--space-compact) var(--space-tight);
  font-size: 0.625rem;
  font-weight: 600;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-family: var(--font-display);
}

.label-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-chop);
  opacity: 0.6;
  flex-shrink: 0;
  box-shadow: 0 0 4px var(--color-chop-glow);
}

.nav-item {
  color: var(--color-parchment-dim);
  margin-bottom: 2px;
  animation: navItemFade 0.35s var(--ease-editorial) both;
  opacity: 0;
  transform: translateX(-6px);
}

@keyframes navItemFade {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.nav-item:hover {
  background: var(--color-ink-wash-light);
  color: var(--color-parchment);
}

.nav-item:hover .nav-icon {
  color: var(--color-parchment);
  transform: translateX(1px);
}

.nav-item--active {
  background: linear-gradient(90deg, var(--color-chop-soft) 0%, rgba(200, 66, 59, 0.05) 100%);
  color: var(--color-chop);
}

.nav-item--active:hover {
  background: linear-gradient(90deg, rgba(200, 66, 59, 0.2) 0%, rgba(200, 66, 59, 0.08) 100%);
  color: var(--color-chop-light);
}

.nav-indicator {
  background: transparent;
  box-shadow: none;
}

.nav-item--active .nav-indicator {
  background: linear-gradient(180deg, var(--color-chop-light), var(--color-chop-deep));
  box-shadow: 0 0 8px var(--color-chop-glow), 0 0 16px rgba(200, 66, 59, 0.3);
  height: 20px;
}

.nav-icon {
  color: var(--color-parchment-muted);
  transition: all var(--duration-fast) var(--ease-editorial);
}

.nav-item--active .nav-icon {
  color: var(--color-chop-light);
  filter: drop-shadow(0 0 4px var(--color-chop-glow));
}

.nav-text {
  transition: color var(--duration-fast) var(--ease-editorial);
}

.nav-item--active .nav-text {
  text-shadow: 0 0 8px rgba(200, 66, 59, 0.2);
}

.control-area {
  position: relative;
}

.control-divider {
  position: relative;
}

.divider-line {
  height: 1px;
  background: linear-gradient(90deg, 
    transparent 0%,
    var(--color-ink-edge) 20%,
    var(--color-muted-soft) 50%,
    var(--color-ink-edge) 80%,
    transparent 100%
  );
}

.control-btn {
  padding: 0.4rem 0.625rem;
  border-radius: var(--radius-scroll);
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--color-parchment-dim);
  background: linear-gradient(180deg, var(--color-ink-elevated), var(--color-ink-panel));
  border: 1px solid var(--color-ink-edge);
  box-shadow: var(--shadow-inset);
  transition: all var(--duration-fast) var(--ease-editorial);
  cursor: pointer;
  user-select: none;
}

.control-btn:hover {
  background: linear-gradient(180deg, var(--color-ink-highlight), var(--color-ink-elevated));
  color: var(--color-parchment);
  border-color: var(--color-muted-soft);
  transform: translateY(-1px);
}

.control-btn:active {
  transform: translateY(0);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
}

.lang-btn {
  min-width: 36px;
  font-family: var(--font-display);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.main-content {
  animation: mainFadeIn 0.5s var(--ease-page);
}

@keyframes mainFadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.main-inner {
  min-height: 100%;
}

html[data-theme="paper"] .sidebar {
  background-image: 
    linear-gradient(180deg, rgba(255, 255, 255, 0.3) 0%, transparent 20%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='paper'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23paper)' opacity='0.04'/%3E%3C/svg%3E");
}

html[data-theme="paper"] .seal {
  box-shadow: 
    0 2px 8px rgba(168, 54, 47, 0.3),
    0 0 16px rgba(168, 54, 47, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.35),
    inset 0 -1px 0 rgba(0, 0, 0, 0.1);
}

html[data-theme="paper"] .nav-item:hover {
  background: rgba(26, 21, 16, 0.04);
}

html[data-theme="paper"] .nav-item--active {
  background: linear-gradient(90deg, var(--color-chop-soft) 0%, rgba(168, 54, 47, 0.04) 100%);
}

html[data-theme="paper"] .nav-item--active:hover {
  background: linear-gradient(90deg, rgba(168, 54, 47, 0.15) 0%, rgba(168, 54, 47, 0.06) 100%);
}

html[data-theme="paper"] .control-btn {
  background: linear-gradient(180deg, var(--color-paper-warm), var(--color-paper-cream));
  box-shadow: var(--shadow-inset-paper);
}

html[data-theme="paper"] .control-btn:hover {
  background: linear-gradient(180deg, #fffdf8, var(--color-paper-warm));
  border-color: var(--color-paper-edge);
}

@media (prefers-reduced-motion: reduce) {
  .nav-group,
  .nav-item,
  .main-content,
  .seal-glow-layer {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
</style>
