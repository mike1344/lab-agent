// 本地可视化验收：登录 → 首页图表 → 实验室/设备表格 → 审核弹窗（管理员）+ 修改弹窗（学生）。
// 使用系统 Chrome（playwright-core 不下载浏览器），仅本地运行，不进入 CI。
// 用法：node scripts/visual-check.mjs
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const base = process.env.BASE_URL || 'http://localhost:5173'
const chromePath =
  process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const outDir = path.resolve(process.cwd(), '..', 'docs', 'visual-check')
fs.mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
})
const issues = []

async function newPage() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } })
  const page = await context.newPage()
  page.on('pageerror', (error) => issues.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() === 'error') issues.push(`console: ${message.text()}`)
  })
  page.on('requestfailed', (request) =>
    issues.push(`requestfailed: ${request.url()} ${request.failure()?.errorText || ''}`),
  )
  return page
}

async function login(page, username, password) {
  await page.goto(`${base}/login`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForSelector('input[placeholder="请输入用户名"]', { timeout: 15000 })
  await page.fill('input[placeholder="请输入用户名"]', username)
  await page.fill('input[placeholder="请输入密码"]', password)
  await page.getByRole('button', { name: /登\s*录/ }).click()
  await page.waitForURL(/\/home/, { timeout: 20000 })
  await page.waitForTimeout(2000)
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(outDir, name) })
  console.log('saved', name)
}

try {
  const adminPage = await newPage()
  await adminPage.goto(`${base}/login`, { waitUntil: 'networkidle', timeout: 30000 })
  await adminPage.waitForSelector('input[placeholder="请输入用户名"]', { timeout: 15000 })
  await shot(adminPage, '01-login.png')
  await login(adminPage, 'smoke_admin', 'SmokeAdmin123!')
  await shot(adminPage, '02-home.png')

  await adminPage.goto(`${base}/lab`, { waitUntil: 'networkidle' })
  await adminPage.waitForSelector('.el-table', { timeout: 20000 })
  await adminPage.waitForTimeout(800)
  await shot(adminPage, '03-lab.png')

  await adminPage.goto(`${base}/equ`, { waitUntil: 'networkidle' })
  await adminPage.waitForSelector('.el-table', { timeout: 20000 })
  await adminPage.waitForTimeout(800)
  await shot(adminPage, '04-equ.png')

  await adminPage.goto(`${base}/reservation`, { waitUntil: 'networkidle' })
  await adminPage.waitForTimeout(1200)
  await adminPage.getByRole('button', { name: '通过' }).first().click()
  await adminPage.waitForSelector('.el-dialog', { state: 'visible', timeout: 15000 })
  await adminPage.waitForTimeout(600)
  await shot(adminPage, '05-review-dialog.png')

  // 学生视角：待审核预约的“修改”弹窗
  const studentPage = await newPage()
  await login(studentPage, 'pku_cs2401_01', 'Student123456')
  await studentPage.goto(`${base}/reservation`, { waitUntil: 'networkidle' })
  await studentPage.waitForTimeout(1200)
  await studentPage.getByRole('button', { name: '修改' }).first().click()
  await studentPage.waitForSelector('.el-dialog', { state: 'visible', timeout: 15000 })
  await studentPage.waitForTimeout(600)
  await shot(studentPage, '06-edit-dialog.png')

  console.log(issues.length ? `issues:\n${issues.join('\n')}` : 'no page errors captured')
} finally {
  await browser.close()
}
