import assert from 'node:assert/strict'
import test from 'node:test'

import { parseFilename } from '../src/utils/download.js'

test('优先解析 RFC 5987 中文文件名（filename*=UTF-8）', () => {
  const disposition =
    "attachment; filename=%E7%94%A8%E6%88%B7.xlsx; filename*=UTF-8''%E7%94%A8%E6%88%B7%E5%88%97%E8%A1%A8.xlsx"
  assert.equal(parseFilename(disposition, 'fallback.xlsx'), '用户列表.xlsx')
})

test('兼容旧式 filename= 引号写法', () => {
  assert.equal(parseFilename('attachment; filename="report.xlsx"', 'fallback.xlsx'), 'report.xlsx')
})

test('缺失或为空时回落到 fallback', () => {
  assert.equal(parseFilename('', 'fallback.xlsx'), 'fallback.xlsx')
  assert.equal(parseFilename(undefined, 'fallback.xlsx'), 'fallback.xlsx')
})

test('非法百分号编码时返回原始字符串而不抛错', () => {
  assert.equal(parseFilename("attachment; filename*=UTF-8''%E0%A4%A", 'fallback.xlsx'), '%E0%A4%A')
})
