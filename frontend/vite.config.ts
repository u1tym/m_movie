import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const movieTarget = env.VITE_MOVIE_PROXY_TARGET || 'http://127.0.0.1:8000'
  const loginTarget = env.VITE_LOGIN_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [vue()],
    base: '/mobile/movie/',
    server: {
      proxy: {
        '/api/movie': {
          target: movieTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/movie/, '/api/v1/movie'),
        },
        '/api/auth': {
          target: loginTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/auth/, ''),
        },
      },
    },
  }
})
