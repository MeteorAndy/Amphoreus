<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  FolderOpen, Zap, Sparkles, FlaskConical, Globe,
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
  desc: string
}

const navItems: NavItem[] = [
  { labelKey: 'nav.projects', path: '/projects', icon: FolderOpen, desc: '我的项目' },
  { labelKey: 'nav.pipeline', path: '/pipeline', icon: Zap, desc: '一键生成' },
  { labelKey: 'nav.interactive', path: '/interactive', icon: Sparkles, desc: '互动创作' },
  { labelKey: 'nav.sandbox', path: '/sandbox', icon: FlaskConical, desc: '沙盒观察' },
  { labelKey: 'nav.world', path: '/world', icon: Globe, desc: '世界构建' },
  { labelKey: 'nav.characters', path: '/characters', icon: Users, desc: '角色管理' },
  { labelKey: 'nav.plot', path: '/plot', icon: ListTree, desc: '剧情架构' },
  { labelKey: 'nav.scene', path: '/scene', icon: Drama, desc: '场景执行' },
  { labelKey: 'nav.writer', path: '/writer', icon: PenTool, desc: '叙事写作' },
  { labelKey: 'nav.quality', path: '/quality', icon: ShieldCheck, desc: '质量审稿' },
]

const activeIndex = computed(() =>
  navItems.findIndex((item) => route.path.startsWith(item.path)),
)

function navigate(path: string): void {
  router.push(path)
}

function toggleLang(): void {
  setLang(currentLang.value === 'zh' ? 'en' : 'zh')
}
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-ink-bg">
    <!-- Sidebar -->
    <aside class="flex flex-col w-56 bg-ink-panel border-r border-ink-edge flex-shrink-0">
      <!-- Masthead -->
      <div class="flex items-center gap-2.5 px-4 h-14 border-b border-ink-edge">
        <div class="w-8 h-8 rounded-seal bg-chop flex items-center justify-center flex-shrink-0 shadow-sm">
          <BookOpen :size="16" class="text-white" :stroke-width="2" />
        </div>
        <div class="min-w-0">
          <div class="font-display font-semibold text-parchment text-sm leading-tight truncate">Amphoreus</div>
          <div class="text-[0.65rem] text-muted leading-tight">{{ t('app.title') }}</div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto py-3 px-2">
        <button
          v-for="(item, idx) in navItems"
          :key="item.path"
          @click="navigate(item.path)"
          class="group w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-all relative mb-0.5"
          :class="idx === activeIndex
            ? 'bg-chop/15 text-chop'
            : 'text-parchment-dim hover:bg-ink-elevated hover:text-parchment'"
        >
          <span
            class="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full transition-all"
            :class="idx === activeIndex ? 'bg-chop' : 'bg-transparent'"
          />
          <component :is="item.icon" :size="16" :stroke-width="idx === activeIndex ? 2 : 1.5" class="flex-shrink-0" />
          <span class="font-medium leading-tight">{{ t(item.labelKey) }}</span>
        </button>
      </nav>

      <!-- Bottom controls -->
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

    <!-- Main content -->
    <main class="flex-1 overflow-y-auto">
      <div class="max-w-7xl mx-auto px-8 py-6">
        <slot />
      </div>
    </main>

    <ToastContainer />
  </div>
</template>
