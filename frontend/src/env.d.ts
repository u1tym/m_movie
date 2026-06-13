/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_DEBUG: string
  readonly VITE_MOVIE_ORIGIN: string
  readonly VITE_LOGIN_ORIGIN: string
  readonly VITE_MOVIE_PROXY_TARGET: string
  readonly VITE_LOGIN_PROXY_TARGET: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
