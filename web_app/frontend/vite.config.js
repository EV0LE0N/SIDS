import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  base: './',  // 支持非根路径部署
  root: '.',
  publicDir: 'public',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    emptyOutDir: false // 极其重要：禁止 Vite 删库重建 dist 目录，否则会导致 Docker 的 Nginx 挂载卷 inode 失效，页面一直显示老版本
    // 严禁添加 rollupOptions.input 配置！
    // Vite 会自动读取根目录下的 index.html 作为入口
  }
})