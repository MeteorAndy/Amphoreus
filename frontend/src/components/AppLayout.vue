<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  FolderOpen, Zap, Sparkles, FlaskConical, Globe,
  Users, List, Drama, PenTool, ShieldCheck,
} from 'lucide-vue-next'
import { useI18n } from '../i18n'
import ToastContainer from './ToastContainer.vue'

const { t, setLang, currentLang } = useI18n()
const route = useRoute()
const router = useRouter()

interface NavItem {
  labelKey: string
  path: string
  icon: Component
}

const navItems: NavItem[] = [
  { labelKey: 'nav.projects', path: '/projects', icon: FolderOpen },
  { labelKey: 'nav.pipeline', path: '/pipeline', icon: Zap },
  { labelKey: 'nav.interactive', path: '/interactive', icon: Sparkles },
  { labelKey: 'nav.sandbox', path: '/sandbox', icon: FlaskConical },
  { labelKey: 'nav.world', path: '/world', icon: Globe },
  { labelKey: 'nav.characters', path: '/characters', icon: Users },
  { labelKey: 'nav.plot', path: '/plot', icon: List },
  { labelKey: 'nav.scene', path: '/scene', icon: Drama },
  { labelKey: 'nav.writer', path: '/writer', icon: PenTool },
  { labelKey: 'nav.quality', path: '/quality', icon: ShieldCheck },
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
    <!-- Sidebar: manuscript rail -->
    <aside class="flex flex-col w-20 bg-ink-panel border-r border-ink-edge flex-shrink-0">
      <!-- Masthead: vermillion seal + serif wordmark -->
      <div class="flex flex-col items-center justify-center h-16 border-b border-ink-edge">
        <div class="w-7 h-7 rounded-seal bg-chop flex items-center justify-center mb-0.5">
          <span class="text-xs font-display font-bold text-ink-bg">Am</span>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex flex-col flex-1 py-3 overflow-y-auto">
        <button
          v-for="(item, idx) in navItems"
          :key="item.path"
          @click="navigate(item.path)"
          class="group flex flex-col items-center gap-1 py-2.5 text-[0.65rem] transition-colors relative"
          :class="idx === activeIndex ? 'text-chop' : 'text-muted hover:text-parchment-dim'"
        >
          <span
            class="w-0.5 h-7 absolute left-0 top-1/2 -translate-y-1/2 rounded-r-full transition-all"
            :class="idx === activeIndex ? 'bg-chop' : 'bg-transparent group-hover:bg-ink-edge'"
          />
          <component :is="item.icon" :size="18" :stroke-width="1.5" />
          <span class="leading-tight text-center">{{ t(item.labelKey) }}</span>
        </button>
      </nav>

      <!-- Language toggle -->
      <div class="flex flex-col items-center gap-2 py-3 border-t border-ink-edge">
        <button
          @click="toggleLang"
          class="text-[0.65rem] text-muted hover:text-parchment-dim transition-colors px-2 py-1 rounded hover:bg-ink-elevated"
          :title="t('lang.switch')"
        >
          {{ t('lang.switch') }}
        </button>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-y-auto">
      <div class="max-w-7xl mx-auto p-6">
        <slot />
      </div>
    </main>

    <ToastContainer />
  </div>
</template>
