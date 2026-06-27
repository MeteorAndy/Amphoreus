<script setup lang="ts">
import AppLayout from './components/AppLayout.vue'
import ChatPanel from './components/ChatPanel.vue'
import { useGlobalChat } from './composables/useGlobalChat'

const { messages, loading, sendMessage } = useGlobalChat()
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
        :messages="messages"
        :loading="loading"
        :embedded="true"
        placeholder="有什么可以帮助你的？"
        @send="sendMessage"
      />
    </template>
  </AppLayout>
</template>
