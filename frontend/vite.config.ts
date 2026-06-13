import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // 127.0.0.1 より localhost の方が Windows 環境で安定することがある
  const movieTarget = env.VITE_MOVIE_PROXY_TARGET || 'http://localhost:8000'
  const loginTarget = env.VITE_LOGIN_PROXY_TARGET || 'http://localhost:8000'

  const movieProxy = {
    target: movieTarget,
    changeOrigin: true,
    timeout: 30_000,
    proxyTimeout: 30_000,
  }

  return {
    plugins: [vue()],
    base: '/mobile/movie/',
    server: {
      host: true,
      port: 5173,
      proxy: {
        // フロントは /api/movie を使用（rewrite で /api/v1/movie へ転送）
        '/api/movie': {
          ...movieProxy,
          rewrite: (path) => path.replace(/^\/api\/movie/, '/api/v1/movie'),
        },
        // 直接 /api/v1/movie で呼ばれた場合のフォールバック
        '/api/v1/movie': {
          ...movieProxy,
        },
        '/api/auth': {
          target: loginTarget,
          changeOrigin: true,
          timeout: 30_000,
          proxyTimeout: 30_000,
          rewrite: (path) => path.replace(/^\/api\/auth/, ''),
        },
      },
    },
  }
})
