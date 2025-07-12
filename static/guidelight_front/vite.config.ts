import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// @ts-ignore
import { fileURLToPath, URL } from 'url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // @ts-ignore
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    open: true,
    proxy: {
      // API 代理
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      // 视频流代理
      '/d_estimator': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/f_detector': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/f_tracker': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/g_recognition': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/g_recognizer': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/m_detector': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/p_video': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/s_RGB': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/enhanced_detector': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/location': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
