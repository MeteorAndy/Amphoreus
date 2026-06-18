import { ref } from 'vue'

type Theme = 'ink' | 'paper'

const STORAGE_KEY = 'amphoreus-theme'

const isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined'

const theme = ref<Theme>(
  isBrowser ? ((localStorage.getItem(STORAGE_KEY) as Theme) || 'ink') : 'ink',
)

function applyTheme(t: Theme): void {
  if (!isBrowser) return
  document.documentElement.setAttribute('data-theme', t)
  localStorage.setItem(STORAGE_KEY, t)
  if (t === 'paper') {
    document.body.style.backgroundColor = '#f6f0e4'
    document.body.style.color = '#1a1a1a'
  } else {
    document.body.style.backgroundColor = '#14110e'
    document.body.style.color = '#e8dfcf'
  }
}

if (isBrowser) applyTheme(theme.value)

export function useTheme() {
  function toggle(): void {
    theme.value = theme.value === 'ink' ? 'paper' : 'ink'
    applyTheme(theme.value)
  }

  return { theme, toggle }
}
