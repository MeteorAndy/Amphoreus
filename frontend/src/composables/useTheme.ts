import { ref } from 'vue'

type Theme = 'ink' | 'paper'

const STORAGE_KEY = 'amphoreus-theme'

const theme = ref<Theme>(
  (localStorage.getItem(STORAGE_KEY) as Theme) || 'ink',
)

function applyTheme(t: Theme): void {
  document.documentElement.setAttribute('data-theme', t)
  localStorage.setItem(STORAGE_KEY, t)
}

// Apply on module load
applyTheme(theme.value)

export function useTheme() {
  function toggle(): void {
    theme.value = theme.value === 'ink' ? 'paper' : 'ink'
    applyTheme(theme.value)
  }

  return { theme, toggle }
}
