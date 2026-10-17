import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { parseEnv } from 'node:util'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const envPath = path.resolve(import.meta.dirname, '../../.env')
const filePort = existsSync(envPath) ? parseEnv(readFileSync(envPath, 'utf8')).APP_PORT : undefined
const appPort = (process.env.APP_PORT ?? filePort) || '8082'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, './src') } },
  server: { proxy: { '/api': `http://127.0.0.1:${appPort}` } },
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'] },
})
