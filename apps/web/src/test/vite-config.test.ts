// @vitest-environment node
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

import { afterEach, expect, test } from 'vitest'
import { resolveConfig, type ResolvedConfig } from 'vite'

const webRoot = path.resolve(import.meta.dirname, '../..')
const originalPort = process.env.APP_PORT
const fixtures: string[] = []

test('does_not_expose_database_password_to_client', async () => {
  const config = await resolveFixture('APP_PORT=18082\nPOSTGRES_PASSWORD=fixture-password\n', undefined)
  expect(config.env.POSTGRES_PASSWORD).toBeUndefined()
})

test('uses_shell_port_without_root_env', async () => {
  const config = await resolveFixture(undefined, '18083')
  expect(config.server.proxy?.['/api']).toBe('http://127.0.0.1:18083')
})

test('empty_shell_port_overrides_repository_env', async () => {
  const config = await resolveFixture('APP_PORT=18082\n', '')
  expect(config.server.proxy?.['/api']).toBe('http://127.0.0.1:8082')
})

test('defaults_to_8082_with_empty_file_port', async () => {
  const config = await resolveFixture('APP_PORT=\n', undefined)
  expect(config.server.proxy?.['/api']).toBe('http://127.0.0.1:8082')
})

afterEach(() => {
  if (originalPort === undefined) delete process.env.APP_PORT
  else process.env.APP_PORT = originalPort
  for (const fixture of fixtures.splice(0)) rmSync(fixture, { recursive: true, force: true })
})

async function resolveFixture(
  envFile: string | undefined,
  shellPort: string | undefined,
): Promise<ResolvedConfig> {
  const fixture = mkdtempSync(path.join(tmpdir(), 'cgu-vite-config-'))
  fixtures.push(fixture)
  const root = path.join(fixture, 'apps/web')
  mkdirSync(root, { recursive: true })
  copyFileSync(path.join(webRoot, 'package.json'), path.join(root, 'package.json'))
  copyFileSync(path.join(webRoot, 'vite.config.ts'), path.join(root, 'vite.config.ts'))
  symlinkSync(path.join(webRoot, 'node_modules'), path.join(root, 'node_modules'), 'dir')
  if (envFile !== undefined) writeFileSync(path.join(fixture, '.env'), envFile)
  if (shellPort === undefined) delete process.env.APP_PORT
  else process.env.APP_PORT = shellPort
  return resolveConfig({ root, configFile: path.join(root, 'vite.config.ts'), mode: 'test' }, 'serve')
}

test('defaults_to_8082_without_root_env', async () => {
  const config = await resolveFixture(undefined, undefined)
  expect(config.server.proxy?.['/api']).toBe('http://127.0.0.1:8082')
})

test('uses_port_from_repository_root_env', async () => {
  const config = await resolveFixture('APP_PORT=18082\n', undefined)
  expect(config.server.proxy?.['/api']).toBe('http://127.0.0.1:18082')
})

test('shell_port_overrides_repository_env', async () => {
  const config = await resolveFixture('APP_PORT=18082\n', '18083')
  expect(config.server.proxy?.['/api']).toBe('http://127.0.0.1:18083')
})
