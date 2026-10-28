import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { ElLoading } from 'element-plus'
import App from './App.vue'
import router from './router'
// Element Plus 组件由 unplugin-vue-components 按需引入（见 vite.config.js），
// 这里只保留全局样式与 v-loading 指令，保证主题/加载态一致。
import 'element-plus/dist/index.css'
import './assets/css/global.css'
const app = createApp(App)
// 指令不走组件解析器，显式注册最稳妥（全局样式已包含 el-loading 的样式）
app.directive('loading', ElLoading.directive)
app.use(createPinia())
app.use(router)
app.mount('#app')
