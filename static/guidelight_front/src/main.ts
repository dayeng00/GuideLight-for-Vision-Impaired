import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import './styles/index.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  // @ts-ignore
  app.component(key, component)
}

// 全局配置
// @ts-ignore
app.use(ElementPlus, {
  locale: zhCn
})
app.use(router)

app.mount('#app')
