import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    // Element Plus 按需引入：模板里的 el-* 组件与 ElMessage 等 API 自动注册/导入，
    // 不再整包 import。样式仍使用全局 index.css，避免按需样式带来的视觉回归。
    AutoImport({ resolvers: [ElementPlusResolver({ importStyle: false })], dts: false }),
    Components({ resolvers: [ElementPlusResolver({ importStyle: false })], dts: false }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('element-plus')) return 'vendor-element'
          if (id.includes('echarts')) return 'vendor-echarts'
          if (id.includes('zrender')) return 'vendor-zrender'
          if (id.includes('/vue/') || id.includes('vue-router') || id.includes('pinia')) return 'vendor-vue'
        },
      },
    },
  },
})
