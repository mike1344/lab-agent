import assert from 'node:assert/strict'
import test from 'node:test'

// 在导入 auth.js 之前注入 localStorage 桩，模拟浏览器存储
const store = new Map()
globalThis.localStorage = {
  getItem: (key) => (store.has(key) ? store.get(key) : null),
  setItem: (key, value) => store.set(key, String(value)),
  removeItem: (key) => store.delete(key)
}

const {
  getToken,
  setToken,
  removeToken,
  getRefreshToken,
  setRefreshToken,
  removeRefreshToken,
  getUserInfo,
  setUserInfo,
  logout
} = await import('../src/utils/auth.js')

test('access / refresh token 读写与登出清理', () => {
  setToken('access-token')
  setRefreshToken('refresh-token')
  assert.equal(getToken(), 'access-token')
  assert.equal(getRefreshToken(), 'refresh-token')

  setUserInfo({ username: 'admin', is_superuser: true })
  assert.deepEqual(getUserInfo(), { username: 'admin', is_superuser: true })

  logout()
  assert.equal(getToken(), null)
  assert.equal(getRefreshToken(), null)
  assert.equal(getUserInfo(), null)
})

test('损坏的用户缓存会被清除而不是让应用崩溃', () => {
  localStorage.setItem('userInfo', '{not-json')
  assert.equal(getUserInfo(), null)
  assert.equal(localStorage.getItem('userInfo'), null)
})

test('removeToken / removeRefreshToken 单独可用', () => {
  setToken('a')
  setRefreshToken('b')
  removeToken()
  removeRefreshToken()
  assert.equal(getToken(), null)
  assert.equal(getRefreshToken(), null)
})
