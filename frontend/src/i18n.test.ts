import { describe, it, expect, afterEach } from 'vitest'
import { useI18n } from './i18n'

describe('useI18n', () => {
  const { t, setLang, currentLang } = useI18n()
  const original = currentLang.value

  afterEach(() => {
    setLang(original)
  })

  it('returns the zh string for a known key', () => {
    setLang('zh')
    expect(t('app.title')).toBe('Amphoreus 故事引擎')
  })

  it('returns the en string for a known key', () => {
    setLang('en')
    expect(t('app.title')).toBe('Amphoreus Story Engine')
  })

  it('falls back to the key itself when missing', () => {
    setLang('en')
    expect(t('does.not.exist')).toBe('does.not.exist')
  })

  it('setLang switches the active language and updates currentLang ref', () => {
    setLang('zh')
    expect(currentLang.value).toBe('zh')
    expect(t('nav.world')).toBe('世界构建')

    setLang('en')
    expect(currentLang.value).toBe('en')
    expect(t('nav.world')).toBe('World')
  })

  it('persists the selected language to localStorage', () => {
    setLang('en')
    expect(localStorage.getItem('amphoreus-lang')).toBe('en')
    setLang('zh')
    expect(localStorage.getItem('amphoreus-lang')).toBe('zh')
  })
})
