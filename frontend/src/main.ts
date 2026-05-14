import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(router)

// Initialize language from localStorage on startup
const savedLang = localStorage.getItem('amphoreus-lang')
if (savedLang) {
  document.documentElement.lang = savedLang
}

app.mount('#app')
