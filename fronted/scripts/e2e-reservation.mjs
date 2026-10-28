// 浏览器端到端验收：学生修改待审核预约 → 教师审核通过 → 学生看到已通过。
// 依赖 scripts/seed_e2e.py 准备账号和数据；前端需指向 E2E 后端。
// 用法（fronted 目录）：
//   $env:BASE_URL="http://127.0.0.1:5174"; node scripts/e2e-reservation.mjs
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const outDir = path.resolve(process.cwd(), '..', 'docs', 'visual-check')
fs.mkdirSync(outDir, { recursive: true })

const issues = []
const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
})

function watch(page) {
  page.on('pageerror', (error) => issues.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('WebSocket')) {
      issues.push(`console: ${message.text()}`)
    }
  })
  page.on('requestfailed', (request) => {
    if (!request.url().includes('/api/ws/')) issues.push(`requestfailed: ${request.url()}`)
  })
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(outDir, name) })
  console.log('saved', name)
}

async function login(page, username, password) {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForSelector('input[placeholder="请输入用户名"]', { timeout: 15000 })
  await page.fill('input[placeholder="请输入用户名"]', username)
  await page.fill('input[placeholder="请输入密码"]', password)
  await page.getByRole('button', { name: /登\s*录/ }).click()
  await page.waitForURL(/\/home/, { timeout: 20000 })
  await page.waitForTimeout(1000)
}

try {
  // ===== 学生：打开待审核预约并修改用途 =====
  const studentContext = await browser.newContext({ viewport: { width: 1440, height: 960 } })
  const student = await studentContext.newPage()
  watch(student)
  await login(student, 'e2e_student', 'E2eStudent123!')

  await student.goto(`${base}/reservation`, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await student.waitForSelector('.el-table__row', { timeout: 20000 })
  const studentRow = student.locator('.el-table__row').filter({ hasText: 'E2E 演示实验室' }).first()
  await studentRow.waitFor({ state: 'visible', timeout: 15000 })
  await shot(student, '11-e2e-student-pending.png')

  await studentRow.getByRole('button', { name: '修改' }).click()
  const editDialog = student.locator('.el-dialog').filter({ hasText: '修改预约' }).first()
  await editDialog.waitFor({ state: 'visible', timeout: 15000 })
  const purposeInput = editDialog.locator('textarea').first()
  await purposeInput.fill('E2E 验收：学生修改后的用途')
  await editDialog.getByRole('button', { name: '保存修改' }).click()
  await student.getByText('预约已修改').first().waitFor({ state: 'visible', timeout: 15000 })

  // ===== 教师：审核通过 =====
  const teacherContext = await browser.newContext({ viewport: { width: 1440, height: 960 } })
  const teacher = await teacherContext.newPage()
  watch(teacher)
  await login(teacher, 'e2e_teacher', 'E2eTeacher123!')

  await teacher.goto(`${base}/reservation`, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await teacher.waitForSelector('.el-table__row', { timeout: 20000 })
  const teacherRow = teacher
    .locator('.el-table__row')
    .filter({ hasText: 'E2E 演示实验室' })
    .filter({ hasText: 'E2E 学生' })
    .first()
  await teacherRow.waitFor({ state: 'visible', timeout: 15000 })
  await teacherRow.getByRole('button', { name: '通过' }).click()

  const reviewDialog = teacher.locator('.el-dialog').filter({ hasText: '通过预约' }).first()
  await reviewDialog.waitFor({ state: 'visible', timeout: 15000 })
  await reviewDialog.locator('textarea').first().fill('E2E 验收：教师审核通过')
  await shot(teacher, '12-e2e-teacher-review.png')
  await reviewDialog.getByRole('button', { name: '确认' }).click()
  await teacher.getByText('预约审核完成').first().waitFor({ state: 'visible', timeout: 15000 })

  // ===== 学生：刷新后看到已通过 =====
  await student.reload({ waitUntil: 'domcontentloaded' })
  await student.waitForSelector('.el-table__row', { timeout: 20000 })
  const approvedRow = student.locator('.el-table__row').filter({ hasText: 'E2E 演示实验室' }).first()
  await approvedRow.locator('.el-tag').filter({ hasText: '已通过' }).first().waitFor({ state: 'visible', timeout: 15000 })
  await shot(student, '13-e2e-approved.png')

  if (issues.length) {
    console.log('E2E 过程中捕获到页面错误：')
    for (const issue of issues) console.log(' -', issue)
    process.exitCode = 1
  } else {
    console.log('E2E PASSED: 学生修改 → 教师通过 → 学生看到已通过，无页面错误')
  }
} catch (error) {
  console.log('E2E FAILED:', error.message)
  console.log('issues:', issues.join('\n') || '(none)')
  process.exitCode = 1
} finally {
  await browser.close()
}