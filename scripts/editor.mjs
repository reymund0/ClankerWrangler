#!/usr/bin/env node

import { spawn } from 'node:child_process'
import { request as createHttpRequest } from 'node:http'
import { access, readFile } from 'node:fs/promises'
import { constants as fsConstants } from 'node:fs'
import { dirname, isAbsolute, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { timingSafeEqual } from 'node:crypto'

const scriptPath = fileURLToPath(import.meta.url)
const repositoryRoot = resolve(dirname(scriptPath), '..')
const editorRoot = join(repositoryRoot, 'routing-editor')
const helperPath = join(repositoryRoot, 'subagents', 'scripts', 'routing_editor.py')
const assetRoot = join(editorRoot, 'dist')
const startupTimeoutMs = 10_000
const compatibility = { schema_version: 1, policy_version: '2' }

const usage = `Usage: node scripts/editor.mjs <start|dev|build> [options]

Commands:
  start                    Serve the compatible built editor through Python.
  dev                      Run Python plus Vite with hot reload.
  build                    Build the editor from source.

Options:
  --project PATH           Existing project whose routing overrides may be edited.
  --global-config-dir PATH Alternative global preferences directory.
  --help                   Show this help message.
`

export function parseArguments(argv) {
  const args = [...argv]
  if (args.length === 0 || args[0] === '--help') return { help: true }

  const mode = args.shift()
  if (!['start', 'dev', 'build'].includes(mode)) {
    throw new Error(`Unknown command: ${mode}`)
  }

  const options = { mode, project: undefined, globalConfigDir: undefined }
  while (args.length > 0) {
    const option = args.shift()
    if (option === '--help') return { help: true }
    if (option !== '--project' && option !== '--global-config-dir') {
      throw new Error(`Unknown option: ${option}`)
    }
    const value = args.shift()
    if (!value || value.startsWith('--')) {
      throw new Error(`${option} requires a path`)
    }
    const key = option === '--project' ? 'project' : 'globalConfigDir'
    if (options[key] !== undefined) throw new Error(`${option} may be specified only once`)
    options[key] = isAbsolute(value) ? resolve(value) : resolve(process.cwd(), value)
  }
  return options
}

function commandError(message) {
  const error = new Error(message)
  error.exitCode = 2
  return error
}

async function exists(path) {
  try {
    await access(path, fsConstants.F_OK)
    return true
  } catch {
    return false
  }
}

export async function assertCompatibleBuild() {
  const [indexPresent, manifestPresent] = await Promise.all([
    exists(join(assetRoot, 'index.html')),
    exists(join(assetRoot, 'compatibility.json')),
  ])
  if (!indexPresent || !manifestPresent) {
    throw new Error('Editor build is unavailable. Run "npm run editor:build" first.')
  }

  let manifest
  try {
    manifest = JSON.parse(await readFile(join(assetRoot, 'compatibility.json'), 'utf8'))
  } catch {
    throw new Error('Editor build is incompatible. Run "npm run editor:build" first.')
  }
  if (manifest?.schema_version !== compatibility.schema_version || manifest?.policy_version !== compatibility.policy_version) {
    throw new Error('Editor build is incompatible. Run "npm run editor:build" first.')
  }
}

function waitForExit(child, timeoutMs) {
  return new Promise((resolveExit) => {
    let timer
    const complete = (exited) => {
      clearTimeout(timer)
      child.removeListener('exit', onExit)
      resolveExit(exited)
    }
    const onExit = () => complete(true)
    child.once('exit', onExit)
    if (timeoutMs !== undefined) timer = setTimeout(() => complete(false), timeoutMs)
  })
}

function settleWithin(promise, timeoutMs) {
  return new Promise((resolveWithin) => {
    let timer
    const complete = (value) => {
      clearTimeout(timer)
      resolveWithin(value)
    }
    timer = setTimeout(() => complete(false), timeoutMs)
    promise.then(() => complete(true), () => complete(true))
  })
}

function run(command, args, options = {}) {
  return new Promise((resolveRun, rejectRun) => {
    const child = spawn(command, args, { shell: false, windowsHide: true, ...options })
    child.once('error', rejectRun)
    child.once('exit', (code, signal) => {
      if (code === 0) resolveRun()
      else rejectRun(new Error(`${command} exited with ${signal ?? `code ${code}`}`))
    })
  })
}

function inspectPython(command, prefix) {
  return new Promise((resolvePython) => {
    const child = spawn(command, [...prefix, '-c', 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}|{sys.executable}")'], {
      shell: false,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    let output = ''
    let settled = false
    const settle = (value) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolvePython(value)
    }
    const timer = setTimeout(() => {
      child.kill()
      settle(null)
    }, 5_000)
    child.stdout.on('data', (chunk) => { output += chunk })
    child.once('error', () => settle(null))
    child.once('exit', (code) => {
      const match = output.trim().match(/^(\d+)\.(\d+)\|(.+)$/)
      if (code !== 0 || !match) return settle(null)
      const major = Number(match[1])
      const minor = Number(match[2])
      settle(major === 3 && minor >= 10 ? { command: match[3], prefix: [] } : null)
    })
  })
}

export async function discoverPython(environment = process.env, platform = process.platform) {
  if (environment.CLANKER_PYTHON) {
    const selected = await inspectPython(environment.CLANKER_PYTHON, [])
    if (selected) return selected
    throw new Error('CLANKER_PYTHON must name a runnable Python 3.10+ executable.')
  }

  const candidates = platform === 'win32'
    ? [{ command: 'py', prefix: ['-3'] }, { command: 'python3', prefix: [] }, { command: 'python', prefix: [] }]
    : [{ command: 'python3', prefix: [] }, { command: 'python', prefix: [] }]
  for (const candidate of candidates) {
    const selected = await inspectPython(candidate.command, candidate.prefix)
    if (selected) return selected
  }
  throw new Error('Python 3.10+ is required. Install it or set CLANKER_PYTHON to its executable path.')
}

function parsePythonBootstrap(line) {
  const match = line.match(/^Open the local editor: (http:\/\/127\.0\.0\.1:(\d{1,5})\/#token=([A-Za-z0-9_-]{20,}))$/)
  if (!match) return null
  const port = Number(match[2])
  if (port < 1 || port > 65_535) return null
  return { line, origin: `http://127.0.0.1:${port}`, token: match[3] }
}

function secureEqual(actual, expected) {
  if (typeof actual !== 'string') return false
  const left = Buffer.from(actual)
  const right = Buffer.from(expected)
  return left.length === right.length && timingSafeEqual(left, right)
}

function apiPath(path) {
  return path === '/api' || path.startsWith('/api/')
}

function reject(res, message) {
  if (!res.headersSent) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' })
  }
  res.end(message)
}

function createApiMiddleware(backend, getViteOrigin) {
  const backendUrl = new URL(backend.origin)
  const backendHost = backendUrl.host
  return (req, res, next) => {
    if (!apiPath(req.url ?? '')) return next()

    const viteOrigin = getViteOrigin()
    const viteHost = viteOrigin.replace('http://', '')
    const host = req.headers.host
    const origin = req.headers.origin
    const token = req.headers['x-clanker-token']
    if (host !== viteHost) return reject(res, 'Unexpected Host')
    if (origin !== undefined && origin !== viteOrigin) return reject(res, 'Unexpected Origin')
    if (req.method === 'POST' && origin !== viteOrigin) return reject(res, 'A same-origin request is required')
    if (!secureEqual(token, backend.token)) return reject(res, 'Editor session authorization is required')

    const headers = { ...req.headers, host: backendHost }
    if (origin !== undefined) headers.origin = backend.origin
    const proxy = createHttpRequest({
      hostname: backendUrl.hostname,
      port: backendUrl.port,
      method: req.method,
      path: req.url,
      headers,
    }, (response) => {
      res.writeHead(response.statusCode ?? 502, response.headers)
      response.pipe(res)
    })
    proxy.once('error', () => {
      if (!res.headersSent) {
        res.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' })
      }
      res.end('The local editor service is unavailable')
    })
    req.once('aborted', () => proxy.destroy())
    req.pipe(proxy)
  }
}

function createLifecycle() {
  let python = null
  let vite = null
  let stopping = false
  let completed = false
  let complete
  const done = new Promise((resolveDone) => { complete = resolveDone })

  const finish = (exitCode) => {
    if (completed) return
    completed = true
    complete(exitCode)
  }

  async function stopPython() {
    if (!python || python.exitCode !== null || python.signalCode !== null) return
    const exited = waitForExit(python, 5_000)
    python.kill('SIGTERM')
    if (await exited || python.exitCode !== null || python.signalCode !== null) return
    const forcedExit = waitForExit(python, 1_000)
    python.kill('SIGKILL')
    await forcedExit
  }

  async function stopVite() {
    if (!vite) return
    const closed = await settleWithin(vite.close(), 5_000)
    if (!closed) {
      vite.httpServer?.closeAllConnections?.()
      await settleWithin(vite.close(), 1_000)
    }
  }

  return {
    get stopping() { return stopping },
    get done() { return done },
    setPython(child) {
      python = child
      if (stopping) void stopPython()
    },
    setVite(server) {
      vite = server
      if (stopping) void server.close()
    },
    async shutdown(exitCode = 0) {
      if (stopping) return done
      stopping = true
      try {
        await stopVite()
      } finally {
        await stopPython()
        finish(exitCode)
      }
      return done
    },
    async fail(message) {
      if (!stopping) process.stderr.write(`${message}\n`)
      return this.shutdown(1)
    },
  }
}

function relayLines(stream, onLine) {
  let pending = ''
  stream.setEncoding('utf8')
  stream.on('data', (chunk) => {
    pending += chunk
    let newline
    while ((newline = pending.indexOf('\n')) >= 0) {
      const line = pending.slice(0, newline).replace(/\r$/, '')
      pending = pending.slice(newline + 1)
      onLine(line)
    }
  })
  stream.on('end', () => {
    if (pending) onLine(pending.replace(/\r$/, ''))
  })
}

async function startPython(options, lifecycle, hideBootstrap) {
  if (lifecycle.stopping) throw new Error('The local editor service stopped during startup.')
  const python = await discoverPython()
  if (lifecycle.stopping) throw new Error('The local editor service stopped during startup.')
  const args = [...python.prefix, '-u', helperPath, '--assets', assetRoot]
  if (options.project) args.push('--project', options.project)
  if (options.globalConfigDir) args.push('--global-config-dir', options.globalConfigDir)

  const child = spawn(python.command, args, {
    shell: false,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  lifecycle.setPython(child)
  if (lifecycle.stopping) {
    child.kill('SIGTERM')
    throw new Error('The local editor service stopped during startup.')
  }

  return new Promise((resolveReady, rejectReady) => {
    let ready = false
    let settled = false
    const settle = (callback, value) => {
      if (settled) return
      settled = true
      clearTimeout(timeout)
      callback(value)
    }
    const timeout = setTimeout(() => {
      settle(rejectReady, new Error('The local editor service did not become ready within 10 seconds.'))
    }, startupTimeoutMs)

    relayLines(child.stdout, (line) => {
      const bootstrap = parsePythonBootstrap(line)
      if (bootstrap && !ready) {
        ready = true
        if (!hideBootstrap) process.stdout.write(`${line}\n`)
        settle(resolveReady, bootstrap)
        return
      }
      process.stdout.write(`${line}\n`)
    })
    relayLines(child.stderr, (line) => process.stderr.write(`${line}\n`))
    child.once('error', (error) => {
      if (!ready) settle(rejectReady, new Error(`Could not start Python: ${error.message}`))
      else void lifecycle.fail(`The local editor service stopped: ${error.message}`)
    })
    child.once('exit', (code, signal) => {
      if (!ready) {
        settle(rejectReady, new Error(`The local editor service stopped before readiness (${signal ?? `code ${code}`}).`))
      } else if (!lifecycle.stopping) {
        void lifecycle.fail(`The local editor service stopped unexpectedly (${signal ?? `code ${code}`}).`)
      }
    })
  })
}

async function startVite(backend, lifecycle) {
  const viteEntry = join(editorRoot, 'node_modules', 'vite', 'dist', 'node', 'index.js')
  if (!await exists(viteEntry)) {
    throw new Error('Editor dependencies are unavailable. In routing-editor run "npm ci", then run "npm run editor:build".')
  }
  const { createServer } = await import(pathToFileURL(viteEntry).href)
  if (lifecycle.stopping) throw new Error('The local editor service stopped during startup.')
  let viteOrigin = null
  const server = await createServer({
    root: editorRoot,
    logLevel: 'error',
    plugins: [{
      name: 'clanker-routing-editor-api-boundary',
      transformIndexHtml() {
        return [{ tag: 'meta', attrs: { name: 'clanker-session-token', content: backend.token }, injectTo: 'head-prepend' }]
      },
      configureServer(viteServer) {
        viteServer.middlewares.use((req, res, next) => {
          const expected = viteOrigin ?? 'http://127.0.0.1:0'
          if (req.headers.host !== new URL(expected).host) return reject(res, 'Unexpected Host')
          if (req.headers.origin !== undefined && req.headers.origin !== expected) return reject(res, 'Unexpected Origin')
          res.setHeader('Cache-Control', 'no-store')
          res.setHeader('Referrer-Policy', 'no-referrer')
          res.setHeader('X-Frame-Options', 'DENY')
          next()
        })
        viteServer.middlewares.use(createApiMiddleware(backend, () => viteOrigin ?? 'http://127.0.0.1:0'))
      },
    }],
    server: { cors: false, host: '127.0.0.1', headers: { 'Cache-Control': 'no-store' } },
  })
  lifecycle.setVite(server)
  if (lifecycle.stopping) throw new Error('The local editor service stopped during startup.')
  await server.listen()
  if (lifecycle.stopping) {
    await server.close()
    throw new Error('The local editor service stopped during startup.')
  }
  const address = server.httpServer?.address()
  if (!address || typeof address === 'string' || !Number.isInteger(address.port) || address.port < 1) {
    throw new Error('Vite did not report a loopback port.')
  }
  viteOrigin = `http://127.0.0.1:${address.port}`
  return viteOrigin
}

async function buildEditor() {
  const tsc = join(editorRoot, 'node_modules', 'typescript', 'bin', 'tsc')
  const vite = join(editorRoot, 'node_modules', 'vite', 'bin', 'vite.js')
  if (!await exists(tsc) || !await exists(vite)) {
    throw new Error('Editor dependencies are unavailable. In routing-editor run "npm ci", then retry "npm run editor:build".')
  }
  await run(process.execPath, [tsc, '-b'], { cwd: editorRoot, stdio: 'inherit' })
  await run(process.execPath, [vite, 'build'], { cwd: editorRoot, stdio: 'inherit' })
}

async function serve(options) {
  await assertCompatibleBuild()
  const lifecycle = createLifecycle()
  const stop = () => { void lifecycle.shutdown(0) }
  process.once('SIGINT', stop)
  process.once('SIGTERM', stop)
  process.once('disconnect', stop)

  try {
    const backend = await startPython(options, lifecycle, options.mode === 'dev')
    if (options.mode === 'start') {
      const exitCode = await lifecycle.done
      if (exitCode !== 0) {
        const error = new Error('The local editor service stopped unexpectedly.')
        error.exitCode = exitCode
        throw error
      }
      return
    }
    if (lifecycle.stopping) {
      const exitCode = await lifecycle.done
      if (exitCode !== 0) {
        const error = new Error('The local editor service stopped unexpectedly.')
        error.exitCode = exitCode
        throw error
      }
      return
    }
    const viteOrigin = await startVite(backend, lifecycle)
    process.stdout.write(`Open the local editor: ${viteOrigin}/#token=${backend.token}\n`)
    const exitCode = await lifecycle.done
    if (exitCode !== 0) {
      const error = new Error('The local editor service stopped unexpectedly.')
      error.exitCode = exitCode
      throw error
    }
  } catch (error) {
    const exitCode = await lifecycle.shutdown(1)
    if (exitCode !== 0) throw error
  } finally {
    process.removeListener('SIGINT', stop)
    process.removeListener('SIGTERM', stop)
    process.removeListener('disconnect', stop)
  }
}

export async function main(argv = process.argv.slice(2)) {
  let options
  try {
    options = parseArguments(argv)
  } catch (error) {
    throw commandError(`${error.message}\n\n${usage}`)
  }
  if (options.help) {
    process.stdout.write(usage)
    return
  }
  if (options.mode === 'build') return buildEditor()
  return serve(options)
}

if (process.argv[1] && resolve(process.argv[1]) === scriptPath) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`)
    process.exitCode = error.exitCode ?? 1
  })
}
