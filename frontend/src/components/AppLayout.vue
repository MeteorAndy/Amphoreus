<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

interface NavItem {
  label: string
  path: string
  icon: string
}

const navItems: NavItem[] = [
  { label: 'World', path: '/world', icon: '🌍' },
  { label: 'Characters', path: '/characters', icon: '👥' },
  { label: 'Plot', path: '/plot', icon: '📋' },
  { label: 'Scene', path: '/scene', icon: '🎭' },
  { label: 'Writer', path: '/writer', icon: '✍️' },
]

const activeIndex = computed(() => {
  return navItems.findIndex((item) => route.path.startsWith(item.path))
})

function navigate(path: string): void {
  router.push(path)
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
          <span>{{ item.label }}</span>
        </button>
      </nav>
      <div class="flex flex-col items-center py-3 border-t border-gray-800">
        <div class="flex gap-1">
          <span
            v-for="i in 5"
            :key="i"
            class="w-2 h-2 rounded-full transition-colors"
            :class="i <= activeIndex + 1 ? 'bg-indigo-500' : 'bg-gray-700'"
          />
        </div>
      </div>
    </aside>
    <main class="flex-1 overflow-y-auto">
      <div class="max-w-7xl mx-auto p-6">
        <slot />
      </div>
    </main>
  </div>
</template>
