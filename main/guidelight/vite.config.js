import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import md from 'vite-plugin-markdown'
// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    md.plugin({
      mode: ['vue'],  // 强制 Vue 组件模式
      markdownIt: {   // 自定义解析器配置
        html: true,
        linkify: true
      }
    })
  ],
  server: {
    proxy: {
      '/api': {  // 👈 关键配置点
        target: 'http://backend-server.com', // 真实后端地址
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '') // 路径重写
      }
    }
  }
})
