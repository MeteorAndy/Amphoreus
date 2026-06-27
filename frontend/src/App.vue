<script setup lang="ts">
import AppLayout from './components/AppLayout.vue'
import ChatPanel from './components/ChatPanel.vue'
import { useAssistant } from './composables/useAssistant'

const assistant = useAssistant()
</script>

<template>
  <AppLayout>
    <router-view v-slot="{ Component }">
      <transition name="page-lift" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    <template #right-panel>
      <ChatPanel
        :messages="assistant.messages.value"
        :loading="assistant.loading.value"
        :suggestions="assistant.suggestions.value"
        :embedded="true"
        :context-title="assistant.currentContext.value.title"
        placeholder="问我任何关于创作的问题，或点击下方建议..."
        @send="assistant.sendMessage"
        @clear="assistant.clearMessages"
      />
    </template>
  </AppLayout>
</template>
