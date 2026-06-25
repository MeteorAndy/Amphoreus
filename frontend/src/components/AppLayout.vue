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
  <div class="flex h-screen overflow-hidden bg-ink-bg">
    <aside class="flex flex-col w-56 bg-ink-panel border-r border-ink-edge flex-shrink-0">
      <div class="flex items-center gap-2.5 px-4 h-14 border-b border-ink-edge">
        <div class="w-8 h-8 rounded-seal bg-chop flex items-center justify-center flex-shrink-0 shadow-sm">
          <BookOpen :size="16" class="text-white" :stroke-width="2" />
        </div>
        <div class="min-w-0">
          <div class="font-display font-semibold text-parchment text-sm leading-tight truncate">Amphoreus</div>
          <div class="text-[0.65rem] text-muted leading-tight">{{ t('app.title') }}</div>
        </div>
      </div>

      <nav class="flex-1 overflow-y-auto py-3 px-2">
        <template v-for="group in navGroups" :key="group.labelKey">
          <div class="px-2.5 pt-3 pb-1 first:pt-0">
            <div class="text-[0.65rem] font-semibold text-muted uppercase tracking-widest">
              {{ t(group.labelKey) }}
            </div>
          </div>
          <button
            v-for="item in group.items"
            :key="item.path"
            @click="navigate(item.path)"
            class="group w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-sm transition-all relative mb-0.5"
            :class="isActive(item.path)
              ? 'bg-chop/15 text-chop'
              : 'text-parchment-dim hover:bg-ink-elevated hover:text-parchment'"
          >
            <span
              class="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r-full transition-all"
              :class="isActive(item.path) ? 'bg-chop' : 'bg-transparent'"
            />
            <component :is="item.icon" :size="15" :stroke-width="isActive(item.path) ? 2 : 1.5" class="flex-shrink-0" />
            <span class="font-medium leading-tight">{{ t(item.labelKey) }}</span>
          </button>
        </template>
      </nav>

      <div class="px-3 py-3 border-t border-ink-edge flex items-center gap-2">
        <button
          @click="toggleTheme"
          class="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-xs text-parchment-dim hover:bg-ink-elevated hover:text-parchment transition-colors"
          :title="theme === 'ink' ? t('theme.paper') : t('theme.ink')"
        >
          <component :is="theme === 'ink' ? Sun : Moon" :size="14" :stroke-width="1.5" />
          <span>{{ theme === 'ink' ? (currentLang === 'zh' ? '纸色' : 'Paper') : (currentLang === 'zh' ? '墨色' : 'Ink') }}</span>
        </button>
        <button
          @click="toggleLang"
          class="flex items-center justify-center px-2 py-1.5 rounded-lg text-xs text-parchment-dim hover:bg-ink-elevated hover:text-parchment transition-colors"
          :title="t('lang.switch')"
        >
          {{ currentLang === 'zh' ? 'EN' : '中' }}
        </button>
      </div>
    </aside>

    <main class="flex-1 overflow-y-auto">
      <div class="max-w-7xl mx-auto px-8 py-6">
        <slot />
      </div>
    </main>

    <ToastContainer />
  </div>
</template>
