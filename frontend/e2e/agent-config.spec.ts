import { test, expect } from '@playwright/test'

test.describe('Agent Config Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('modal opens when clicking configure button', async ({ page }) => {
    const configureButton = page.getByRole('button', { name: /配置/i }).or(
      page.getByText('配置 Agent 团队')
    )

    if (await configureButton.count() > 0) {
      await configureButton.first().click()
      await expect(page.getByText('配置 Agent 团队')).toBeVisible()
    }
  })

  test('preset team selection - only one team highlighted at a time', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const webTeamCard = page.locator('button:has-text("Web 开发团队")').first()
    const backendTeamCard = page.locator('button:has-text("后端开发团队")').first()

    await webTeamCard.click()
    await expect(webTeamCard).toHaveClass(/border-primary-500/)

    await backendTeamCard.click()
    await expect(backendTeamCard).toHaveClass(/border-primary-500/)
    await expect(webTeamCard).not.toHaveClass(/border-primary-500/)
  })

  test('preset team shows correct agent count', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const webTeamCard = page.locator('button:has-text("Web 开发团队")').first()
    await webTeamCard.click()

    const agentCount = page.locator('text=已选择')
    await expect(agentCount).toBeVisible()
  })

  test('individual template toggle works', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const pmTemplate = page.locator('button:has-text("产品经理")').first()
    await pmTemplate.click()

    await expect(page.locator('text=已选择')).toBeVisible()

    await pmTemplate.click()
    await expect(page.locator('text=已选择 (0)')).toBeVisible()
  })

  test('selecting individual template deselects preset team', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const webTeamCard = page.locator('button:has-text("Web 开发团队")').first()
    await webTeamCard.click()
    await expect(webTeamCard).toHaveClass(/border-primary-500/)

    const pmTemplate = page.locator('button:has-text("产品经理")').first()
    await pmTemplate.click()

    await expect(webTeamCard).not.toHaveClass(/border-primary-500/)
  })

  test('confirm button shows correct count', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const pmTemplate = page.locator('button:has-text("产品经理")').first()
    await pmTemplate.click()

    await expect(page.getByText('确认配置 (1)')).toBeVisible()
  })

  test('confirm button disabled when no selection', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const confirmButton = page.getByText('确认配置 (0)')
    await expect(confirmButton).toBeDisabled()
  })

  test('modal closes on cancel', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const cancelButton = page.getByRole('button', { name: '取消' })
    if (await cancelButton.count() > 0) {
      await cancelButton.click()
      await expect(page.getByText('配置 Agent 团队')).not.toBeVisible()
    }
  })

  test('custom name input works', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const pmTemplate = page.locator('button:has-text("产品经理")').first()
    await pmTemplate.click()

    const nameInput = page.locator('input[placeholder="产品经理"]')
    await expect(nameInput).toBeVisible()
    await nameInput.fill('张经理')
    await expect(nameInput).toHaveValue('张经理')
  })
})
