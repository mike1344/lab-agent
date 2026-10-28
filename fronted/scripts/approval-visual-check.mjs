// 审批流页面离线可视化验收：拦截 /api 返回固定数据，只验证页面渲染与交互。
// 用法（fronted 目录）：node scripts/approval-visual-check.mjs
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const outDir = path.resolve(process.cwd(), '..', 'docs', 'visual-check')
fs.mkdirSync(outDir, { recursive: true })

const admin = {
  id: 1,
  username: 'admin',
  email: 'admin@example.com',
  full_name: '系统管理员',
  is_active: true,
  is_superuser: true,
  is_teacher: false,
  avatar_url: null,
}
const teacher = {
  id: 2,
  username: 'teacher_li',
  email: 'teacher_li@example.com',
  full_name: '李老师',
  is_active: true,
  is_superuser: false,
  is_teacher: true,
  avatar_url: null,
}
const labs = [
  { id: 1, name: '智能感知实验室', location: '实训楼 301', capacity: 20, description: '', status: 1 },
  { id: 2, name: '机器人实验室', location: '实训楼 302', capacity: 12, description: '', status: 1 },
]
const flow = {
  id: 1,
  lab_id: 1,
  lab_name: '智能感知实验室',
  name: '重点实验室两级审批',
  description: '导师初审后由管理员终审',
  enabled: true,
  pending_count: 2,
  used_count: 5,
  steps: [
    {
      id: 1,
      step_order: 1,
      name: '导师初审',
      label: '导师初审',
      approver_type: 'user',
      approver_role: null,
      approver_id: 2,
      approver_name: '李老师',
    },
    {
      id: 2,
      step_order: 2,
      name: '管理员终审',
      label: '管理员终审',
      approver_type: 'role',
      approver_role: 'admin',
      approver_name: '管理员',
    },
  ],
}
const reservation = {
  id: 10,
  user_id: 3,
  user_name: '张同学',
  lab_id: 1,
  lab_name: '智能感知实验室',
  reservation_date: '2026-11-01',
  start_time: '09:00:00',
  end_time: '10:00:00',
  purpose: '课程实验',
  status: 'pending',
  review_comment: null,
  create_time: '2026-10-28T09:00:00',
  can_review: true,
  approval: {
    flow_id: 1,
    flow_name: '重点实验室两级审批',
    current_step: 1,
    total_steps: 2,
    current_step_name: '导师初审',
    current_approver: '李老师',
    status: 'in_progress',
    can_review: true,
    is_requester: false,
  },
}
const approvalDetail = {
  flow: { id: 1, name: '重点实验室两级审批', description: '导师初审后由管理员终审', enabled: true },
  current_step: 1,
  total_steps: 2,
  steps: [
    {
      step_order: 1,
      name: '导师初审',
      approver_name: '李老师',
      state: 'pending',
      decision: null,
    },
    {
      step_order: 2,
      name: '管理员终审',
      approver_name: '管理员',
      state: 'upcoming',
      decision: null,
    },
  ],
  decisions: [],
  can_review: true,
  review_mode: 'multi',
}

const ok = (data) => ({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'ok', data }) })
const issues = []

const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
})
const context = await browser.newContext({ viewport: { width: 1440, height: 960 } })
await context.addInitScript(
  ({ user }) => {
    localStorage.setItem('token', 'visual-check-token')
    localStorage.setItem('refreshToken', 'visual-check-refresh')
    localStorage.setItem('userInfo', JSON.stringify(user))
  },
  { user: admin },
)
const page = await context.newPage()
page.on('pageerror', (error) => issues.push(`pageerror: ${error.message}`))
page.on('console', (message) => {
  if (message.type() === 'error' && !message.text().includes('WebSocket')) issues.push(`console: ${message.text()}`)
})
page.on('requestfailed', (request) => {
  if (!request.url().includes('/api/ws/')) issues.push(`requestfailed: ${request.url()}`)
})

await page.route('**/api/**', async (route) => {
  const url = new URL(route.request().url())
  const pathname = url.pathname
  if (pathname === '/api/user/info') return route.fulfill(ok(admin))
  if (pathname === '/api/user') {
    return route.fulfill(ok({ list: [admin, teacher], total: 2, page: 1, page_size: 100 }))
  }
  if (pathname === '/api/labs') return route.fulfill(ok(labs))
  if (pathname === '/api/approval-flows') return route.fulfill(ok([flow]))
  if (pathname === '/api/notifications/unread-count') return route.fulfill(ok({ count: 0 }))
  if (pathname === '/api/notifications/mine') return route.fulfill(ok([]))
  if (pathname === '/api/reservations/10/approval') return route.fulfill(ok(approvalDetail))
  if (pathname === '/api/reservations') return route.fulfill(ok([reservation]))
  return route.fulfill(ok(null))
})

async function shot(name) {
  await page.screenshot({ path: path.join(outDir, name) })
  console.log('saved', name)
}

try {
  await page.goto(`${base}/approval`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForSelector('.el-table', { timeout: 20000 })
  await page.waitForTimeout(800)
  await shot('07-approval-flow.png')

  await page.getByRole('button', { name: '编辑' }).first().click()
  await page.waitForSelector('.el-dialog', { state: 'visible', timeout: 15000 })
  await page.waitForTimeout(600)
  await shot('08-approval-dialog.png')
  await page.keyboard.press('Escape')

  await page.goto(`${base}/reservation`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForSelector('.el-table', { timeout: 20000 })
  await page.waitForTimeout(800)
  await shot('09-reservation-approval.png')

  await page.getByRole('button', { name: '进度' }).first().click()
  await page.waitForSelector('.el-dialog', { state: 'visible', timeout: 15000 })
  await page.waitForTimeout(600)
  await shot('10-approval-progress.png')

  console.log(issues.length ? `issues:\n${issues.join('\n')}` : 'no page errors captured')
} catch (error) {
  console.log('CHECK FAILED:', error.message)
  console.log('issues:', issues.join('\n') || '(none)')
  process.exitCode = 1
} finally {
  await browser.close()
}
