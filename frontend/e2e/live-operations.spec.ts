import { expect, test, type Page } from '@playwright/test'

const shots = '../docs/screenshots'

const viewports = [
  { width: 1920, height: 1080 },
  { width: 1440, height: 900 },
] as const

async function ready(page: Page) {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'RubbleEcho' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'STOP' }).first()).toBeVisible()
  await expect(page.getByText(/sampled points|Loading table geometry|cover not loaded/)).toBeVisible()
}

for (const viewport of viewports) {
  test(`live operations fits ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize({ ...viewport })
    await ready(page)
    const fit = await page.evaluate(() => ({
      scrollHeight: document.documentElement.scrollHeight,
      scrollWidth: document.documentElement.scrollWidth,
      innerHeight: window.innerHeight,
      innerWidth: window.innerWidth,
    }))
    expect(fit.innerWidth).toBe(viewport.width)
    expect(fit.innerHeight).toBe(viewport.height)
    expect(fit.scrollHeight).toBeLessThanOrEqual(fit.innerHeight + 2)
    expect(fit.scrollWidth).toBeLessThanOrEqual(fit.innerWidth + 2)
    for (const label of ['sand table', 'cameras', 'radar', 'ultrasonic', 'acoustic', 'vibration', 'rover', 'evidence', 'event timeline', 'rover controls']) {
      const box = await page.getByRole('button', { name: `Expand ${label}`, exact: true }).boundingBox()
      expect(box, label).not.toBeNull()
      expect(box!.y).toBeGreaterThanOrEqual(0)
      expect(box!.x).toBeGreaterThanOrEqual(0)
      expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height + 1)
      expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1)
    }
    await page.screenshot({
      path: `${shots}/live-${viewport.width}x${viewport.height}.png`,
      fullPage: false,
    })
  })
}

test('map dialog opens and escape closes without hiding stop', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await ready(page)
  await page.getByRole('button', { name: 'Expand sand table' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'STOP' })).toBeVisible()
  await page.screenshot({ path: `${shots}/dialog-map-1440x900.png`, fullPage: false })
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(page.getByRole('button', { name: 'STOP' }).first()).toBeVisible()
})

test('each live panel opens one dialog at a time', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await ready(page)
  const labels = [
    'sand table',
    'cameras',
    'radar',
    'ultrasonic',
    'acoustic',
    'vibration',
    'rover',
    'evidence',
    'event timeline',
    'rover controls',
  ]
  for (const label of labels) {
    await page.getByRole('button', { name: `Expand ${label}`, exact: true }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'STOP' })).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(1)
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
  }
  await page.getByRole('button', { name: /devices online/ }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
})

test('compact 1366x768 still shows stop and the map', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  await ready(page)
  await expect(page.getByRole('button', { name: 'STOP' }).first()).toBeVisible()
  await expect(page.getByRole('img', { name: /Sand table plan/ })).toBeVisible()
  const stop = await page.getByRole('button', { name: 'STOP' }).first().boundingBox()
  expect(stop).not.toBeNull()
  expect(stop!.x + stop!.width).toBeLessThanOrEqual(1366)
  await page.screenshot({ path: `${shots}/live-1366x768.png`, fullPage: false })
})
