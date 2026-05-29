<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '../i18n'
import ToastContainer from './ToastContainer.vue'

const { t, setLang, currentLang } = useI18n()
const route = useRoute()
const router = useRouter()

interface NavItem {
  labelKey: string
  path: string
  icon: string
}

const navItems: NavItem[] = [
  { labelKey: 'nav.projects', path: '/projects', icon: '📁' },
  { labelKey: 'nav.pipeline', path: '/pipeline', icon: '⚡' },
  { labelKey: 'nav.world', path: '/world', icon: '🌍' },
  { labelKey: 'nav.characters', path: '/characters', icon: '👥' },
  { labelKey: 'nav.plot', path: '/plot', icon: '📋' },
  { labelKey: 'nav.scene', path: '/scene', icon: '🎭' },
  { labelKey: 'nav.writer', path: '/writer', icon: '✍️' },
]

const activeIndex = computed(() => {
  return navItems.findIndex((item) => route.path.startsWith(item.path))
})

function navigate(path: string): void {
  router.push(path)
}

function toggleLang(): void {
  setLang(currentLang.value === 'zh' ? 'en' : 'zh')
}
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-gray-950">
    <aside class="flex flex-col w-16 bg-gray-900 border-r border-gray-800 flex-shrink-0">
      <div class="flex items-center justify-center h-14 border-b border-gray-800">
        <span class="text-lg font-bold text-indigo-400">AS</span>
      </div>
      <nav class="flex flex-col flex-1 py-4">
        <button
          v-for="(item, idx) in navItems"
          :key="item.path"
          @click="navigate(item.path)"
          class="flex flex-col items-center gap-1 py-3 text-xs transition-colors relative"
          :class="idx === activeIndex ? 'text-indigo-400' : 'text-gray-500 hover:text-gray-300'"
        >
          <span
            class="w-1 h-8 absolute left-0 top-1/2 -translate-y-1/2 rounded-r-full transition-all"
            :class="idx === activeIndex ? 'bg-indigo-400' : 'bg-transparent'"
          />
          <span class="text-lg">{{ item.icon }}</span>
          <span>{{ t(item.labelKey) }}</span>
        </button>
      </nav>
      <div class="flex flex-col items-center gap-2 py-3 border-t border-gray-800">
        <button
          @click="toggleLang"
          class="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2 py-1 rounded hover:bg-gray-800"
          :title="t('lang.switch')"
        >
          {{ t('lang.switch') }}
        </button>
      </div>
    </aside>
    <main class="flex-1 overflow-y-auto">
      <div class="max-w-7xl mx-auto p-6">
        <slot />
      </div>
    </main>
    <ToastContainer />
  </div>
</template>
