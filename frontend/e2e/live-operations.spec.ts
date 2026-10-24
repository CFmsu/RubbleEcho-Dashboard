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

const desktop = [
  { width: 1920, height: 1080 },
  { width: 1600, height: 900 },
  { width: 1440, height: 900 },
  { width: 1366, height: 768 },
  { width: 1280, height: 800 },
] as const

const expandLabels = [
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
] as const

async function panelBox(page: Page) {
  return page.locator('[data-testid="modal-panel"]').evaluate((panel) => {
    const box = panel.getBoundingClientRect()
    const overlay = panel.closest('dialog')?.getBoundingClientRect()
    const view = window.visualViewport
    return {
      width: box.width,
      height: box.height,
      cx: box.left + box.width / 2,
      cy: box.top + box.height / 2,
      left: box.left,
      top: box.top,
      right: box.right,
      bottom: box.bottom,
      overlayCx: overlay ? overlay.left + overlay.width / 2 : window.innerWidth / 2,
      overlayCy: overlay ? overlay.top + overlay.height / 2 : window.innerHeight / 2,
      vx: view?.offsetLeft ?? 0,
      vy: view?.offsetTop ?? 0,
      vw: view?.width ?? window.innerWidth,
      vh: view?.height ?? window.innerHeight,
    }
  })
}

function expectCenteredSquare(box: Awaited<ReturnType<typeof panelBox>>) {
  const detail = JSON.stringify(box)
  expect(Math.abs(box.cx - box.overlayCx), detail).toBeLessThanOrEqual(2)
  expect(Math.abs(box.cy - box.overlayCy), detail).toBeLessThanOrEqual(2)
  expect(Math.abs(box.cx - (box.vx + box.vw / 2)), detail).toBeLessThanOrEqual(2)
  expect(Math.abs(box.cy - (box.vy + box.vh / 2)), detail).toBeLessThanOrEqual(2)
  expect(Math.abs(box.width - box.height), detail).toBeLessThanOrEqual(2)
  expect(box.left).toBeGreaterThanOrEqual(-1)
  expect(box.top).toBeGreaterThanOrEqual(-1)
  expect(box.right).toBeLessThanOrEqual(box.vx + box.vw + 1)
  expect(box.bottom).toBeLessThanOrEqual(box.vy + box.vh + 1)
  expect(box.width).toBeGreaterThan(240)
}

test('every expanded panel is the same centered square', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await ready(page)
  let origin: { cx: number; cy: number; width: number; height: number } | null = null
  for (const label of expandLabels) {
    await page.getByRole('button', { name: `Expand ${label}`, exact: true }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'STOP' })).toBeVisible()
    const box = await panelBox(page)
    expectCenteredSquare(box)
    if (!origin) origin = box
    expect(Math.abs(box.cx - origin.cx)).toBeLessThanOrEqual(2)
    expect(Math.abs(box.cy - origin.cy)).toBeLessThanOrEqual(2)
    expect(Math.abs(box.width - origin.width)).toBeLessThanOrEqual(2)
    expect(Math.abs(box.height - origin.height)).toBeLessThanOrEqual(2)
    const close = await dialog.getByRole('button', { name: 'Close' }).boundingBox()
    expect(close).not.toBeNull()
    expect(close!.x).toBeGreaterThan(box.cx)
    expect(close!.y).toBeGreaterThanOrEqual(box.top - 1)
    expect(close!.y + close!.height).toBeLessThanOrEqual(box.top + 56)
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
  }
})

for (const viewport of desktop) {
  test(`map modal is square and centered at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize({ ...viewport })
    await ready(page)
    await page.getByRole('button', { name: 'Expand sand table' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    expectCenteredSquare(await panelBox(page))
    const fit = await page.evaluate(() => ({
      scrollHeight: document.documentElement.scrollHeight,
      scrollWidth: document.documentElement.scrollWidth,
      innerHeight: window.innerHeight,
      innerWidth: window.innerWidth,
    }))
    expect(fit.scrollHeight).toBeLessThanOrEqual(fit.innerHeight + 2)
    expect(fit.scrollWidth).toBeLessThanOrEqual(fit.innerWidth + 2)
    await page.screenshot({
      path: `${shots}/modal-map-${viewport.width}x${viewport.height}.png`,
      fullPage: false,
    })
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).toHaveCount(0)
  })
}

test('radar and rover modals match the map center', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await ready(page)
  await page.getByRole('button', { name: 'Expand radar', exact: true }).click()
  const radar = await panelBox(page)
  expectCenteredSquare(radar)
  await page.screenshot({ path: `${shots}/modal-radar-1440x900.png`, fullPage: false })
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Expand rover controls', exact: true }).click()
  const rover = await panelBox(page)
  expectCenteredSquare(rover)
  expect(Math.abs(rover.cx - radar.cx)).toBeLessThanOrEqual(2)
  expect(Math.abs(rover.cy - radar.cy)).toBeLessThanOrEqual(2)
  await page.screenshot({ path: `${shots}/modal-rover-1440x900.png`, fullPage: false })
})

const zoomed = [
  { label: '125', width: 1152, height: 720 },
  { label: '150', width: 960, height: 600 },
  { label: '1920-125', width: 1536, height: 864 },
  { label: '1920-150', width: 1280, height: 720 },
] as const

for (const viewport of zoomed) {
  test(`map modal stays centered at ${viewport.label}% browser zoom layout`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await ready(page)
    await page.getByRole('button', { name: 'Expand sand table' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    expectCenteredSquare(await panelBox(page))
    await page.screenshot({ path: `${shots}/modal-map-zoom-${viewport.label}.png`, fullPage: false })
  })
}

test('resizing the browser keeps the open modal centered', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 })
  await ready(page)
  await page.getByRole('button', { name: 'Expand cameras', exact: true }).click()
  expectCenteredSquare(await panelBox(page))
  await page.setViewportSize({ width: 1280, height: 800 })
  expectCenteredSquare(await panelBox(page))
  await page.setViewportSize({ width: 1920, height: 1080 })
  expectCenteredSquare(await panelBox(page))
})

test('opening a modal does not open another telemetry socket', async ({ page }) => {
  await page.addInitScript(() => {
    const Native = window.WebSocket
    window.WebSocket = new Proxy(Native, {
      construct(target, args) {
        const record = window as Window & { __wsOpens?: number }
        record.__wsOpens = (record.__wsOpens ?? 0) + 1
        return Reflect.construct(target, args)
      },
    })
  })
  await page.setViewportSize({ width: 1440, height: 900 })
  await ready(page)
  const before = await page.evaluate(() => (window as Window & { __wsOpens?: number }).__wsOpens ?? 0)
  expect(before).toBeGreaterThan(0)
  await page.getByRole('button', { name: 'Expand sand table' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  const after = await page.evaluate(() => (window as Window & { __wsOpens?: number }).__wsOpens ?? 0)
  expect(after).toBe(before)
})

test('escape returns focus to the control that opened the modal', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await ready(page)
  const trigger = page.getByRole('button', { name: 'Expand evidence', exact: true })
  await trigger.focus()
  await trigger.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(trigger).toBeFocused()
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
