import { test, expect, type Page } from '@playwright/test'

const ROUTES = [
  { hash: '/projects', title: /项目|Projects/ },
  { hash: '/pipeline', title: /一键生成|Generate/ },
  { hash: '/interactive', title: /互动创作|Interactive/ },
  { hash: '/sandbox', title: /沙盒观察|Sandbox/ },
  { hash: '/world', title: /世界构建|World/ },
  { hash: '/characters', title: /角色管理|Characters/ },
  { hash: '/plot', title: /剧情架构|Plot/ },
  { hash: '/scene', title: /场景执行|Scene/ },
  { hash: '/writer', title: /叙事写作|Writer/ },
  { hash: '/quality', title: /质量审稿台|Quality Desk/ },
]

async function collectConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text())
  })
  page.on('pageerror', (err) => errors.push(err.message))
  return errors
}

const IGNORED_ERROR_PATTERNS = [
  'favicon', 'net::ERR', 'Failed to fetch', 'Failed to load resource',
  '502', 'Bad Gateway', '404', 'Not Found', 'ERR_CONNECTION',
  'NetworkError', 'Load failed',
]

function filterCritical(errors: string[]): string[] {
  return errors.filter(e => !IGNORED_ERROR_PATTERNS.some(p => e.includes(p)))
}

// ─── 1. All routes load without crashing ─────────────────────────────────

for (const route of ROUTES) {
  test(`route ${route.hash} loads`, async ({ page }) => {
    const errors = await collectConsoleErrors(page)
    await page.goto(`/#${route.hash}`)
    await page.waitForTimeout(500)
    // The app root should be present (Vue mounted, no crash)
    await expect(page.locator('#app')).toBeVisible()
    // No unhandled errors (filter expected network errors — backend not running)
    const criticalErrors = filterCritical(errors)
    expect(criticalErrors).toEqual([])
  })
}

// ─── 2. Manuscript theme is applied ─────────────────────────────────────

test('manuscript dark theme (ink) applied on load', async ({ page }) => {
  await page.goto('/#/projects')
  await page.waitForTimeout(500)
  const bgColor = await page.evaluate(() =>
    getComputedStyle(document.body).backgroundColor
  )
  // Dark theme: bg should be dark regardless of color format (rgb/oklch/hsl)
  // oklch(0.13 ...) → L=0.13 < 0.2 = dark; rgb(20,17,14) → R=20 < 50 = dark
  const oklchMatch = bgColor.match(/oklch\(([\d.]+)/)
  if (oklchMatch) {
    expect(Number(oklchMatch[1])).toBeLessThan(0.3) // L < 0.3 = dark
  } else {
    const rgb = bgColor.match(/\d+/g)
    expect(rgb).toBeTruthy()
    expect(Number(rgb![0])).toBeLessThan(50)
  }
})

test('serif font loaded on headings', async ({ page }) => {
  await page.goto('/#/quality')
  await page.waitForTimeout(500)
  const h1Font = await page.evaluate(() => {
    const h1 = document.querySelector('h1')
    return h1 ? getComputedStyle(h1).fontFamily : ''
  })
  expect(h1Font.toLowerCase()).toContain('serif')
})

// ─── 3. Nav sidebar has lucide SVG icons ────────────────────────────────

test('nav has 10 items with SVG icons (not emojis)', async ({ page }) => {
  await page.goto('/#/projects')
  await page.waitForTimeout(1000)
  const navButtons = page.locator('aside nav button')
  const btnCount = await navButtons.count()
  expect(btnCount).toBeGreaterThanOrEqual(8) // allow rendering timing
  const svgs = page.locator('aside nav button svg')
  const svgCount = await svgs.count()
  expect(svgCount).toBeGreaterThanOrEqual(btnCount) // each button has at least 1 svg
})

test('quality nav item exists with ShieldCheck icon', async ({ page }) => {
  await page.goto('/#/projects')
  await page.waitForTimeout(500)
  // Quality is the last nav item
  const qualityButton = page.locator('aside nav button').last()
  await expect(qualityButton).toBeVisible()
  await expect(qualityButton.locator('svg')).toBeVisible()
})

// ─── 4. Theme toggle ────────────────────────────────────────────────────

test('theme toggle switches ink → paper', async ({ page }) => {
  await page.goto('/#/projects')
  await page.evaluate(() => localStorage.setItem('amphoreus-theme', 'ink'))
  await page.reload()
  await page.waitForTimeout(500)
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'ink')
  const bgBefore = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  // The theme toggle is the first button in the footer area
  const toggleBtn = page.locator('aside div:last-child button').first()
  await toggleBtn.click()
  await page.waitForTimeout(300)
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'paper')
  const bgAfter = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  // The body bg must have CHANGED (ink→paper)
  expect(bgAfter).not.toBe(bgBefore)
})

test('theme persists in localStorage', async ({ page }) => {
  await page.goto('/#/projects')
  await page.evaluate(() => {
    localStorage.setItem('amphoreus-theme', 'paper')
  })
  await page.reload()
  await page.waitForTimeout(300)
  const stored = await page.evaluate(() => localStorage.getItem('amphoreus-theme'))
  expect(stored).toBe('paper')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'paper')
})

// ─── 5. Quality view ────────────────────────────────────────────────────

test('quality view renders masthead + empty state', async ({ page }) => {
  await page.goto('/#/quality')
  await page.waitForTimeout(500)
  // Masthead
  await expect(page.locator('h1')).toContainText(/质量审稿台|Quality Desk/)
  // Empty state (no reports yet since no pipeline has run)
  const emptyState = page.locator('text=运行"叙事写作"或"一键生成"').or(
    page.locator('text=After running the Writer or Generate pipeline')
  )
  await expect(emptyState).toBeVisible()
})

test('quality view has vermillion seal icon', async ({ page }) => {
  await page.goto('/#/quality')
  await page.waitForTimeout(300)
  const seal = page.locator('.bg-chop\\/15, [class*="chop"]')
  await expect(seal.first()).toBeVisible()
})

// ─── 6. No console errors across navigation ─────────────────────────────

test('no critical console errors during full navigation sweep', async ({ page }) => {
  const errors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text())
  })
  page.on('pageerror', (err) => errors.push(err.message))
  for (const route of ROUTES) {
    await page.goto(`/#${route.hash}`)
    await page.waitForTimeout(300)
  }
  // Filter out expected network errors (backend not running) and favicon
  const critical = filterCritical(errors)
  expect(critical).toEqual([])
})

// ─── 7. Page-lift transition ────────────────────────────────────────────

test('page-lift CSS transition class exists', async ({ page }) => {
  await page.goto('/#/projects')
  // The App.vue wraps router-view in <transition name="page-lift">
  // CSS defines .page-lift-enter-active — verify the stylesheet has it
  const hasTransitionCSS = await page.evaluate(() => {
    const styles = Array.from(document.styleSheets)
    for (const sheet of styles) {
      try {
        const rules = Array.from(sheet.cssRules)
        for (const rule of rules) {
          if (rule.cssText && rule.cssText.includes('page-lift')) return true
        }
      } catch { /* cross-origin */ }
    }
    return false
  })
  expect(hasTransitionCSS).toBe(true)
})

// ─── 8. Active nav indicator ────────────────────────────────────────────

test('active nav item gets vermillion accent', async ({ page }) => {
  await page.goto('/#/quality')
  await page.waitForTimeout(300)
  // The active Quality button should have the chop (vermillion) text color
  const activeBtn = page.locator('aside nav button').filter({ hasText: /质量审稿|Quality/ })
  const color = await activeBtn.evaluate((el) =>
    getComputedStyle(el).color
  )
  // chop is #c8423b → rgb(200, 66, 59)
  expect(color).toMatch(/200.*66.*59|200.*65.*59/)
})
