/// <reference types="vite/client" />

interface ImportMeta {
  readonly url: string
}

declare module 'url' {
  export function fileURLToPath(url: string | URL): string
  export class URL {
    constructor(input: string, base?: string | URL)
    pathname: string
    // 添加其他URL属性...
  }
} 