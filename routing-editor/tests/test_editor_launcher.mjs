import assert from 'node:assert/strict';
import { fork, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { request } from 'node:http';
import { mkdtemp, mkdir, readFile, rm, copyFile, writeFile, cp, symlink, chmod } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { discoverPython } from '../scripts/editor.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const launcher = path.join(root, 'routing-editor', 'scripts', 'editor.mjs');

test('Python discovery compares actual versions across multiple installs and honors overrides', { skip: process.platform === 'win32' }, async () => {
  const fixture = await mkdtemp(path.join(tmpdir(), 'clanker python installs '));
  try {
    const versions = { python3: '3.9.6', 'python3.9': '3.9.6', 'python3.10': '3.10.14', 'python3.14': '3.14.2', 'python3.11': '3.14.10' };
    for (const [name, version] of Object.entries(versions)) {
      const executable = path.join(fixture, name);
      await writeFile(executable, `#!${process.execPath}\nconsole.log(${JSON.stringify(`${version}|${executable}`)});\n`);
      await chmod(executable, 0o755);
    }
    await writeFile(path.join(fixture, 'python3.99'), 'broken executable');
    const environment = { PATH: fixture };
    assert.equal((await discoverPython(environment, 'linux')).command, path.join(fixture, 'python3.11'));
    assert.equal((await discoverPython({ ...environment, CLANKER_PYTHON: path.join(fixture, 'python3.10') }, 'linux')).command, path.join(fixture, 'python3.10'));
    await assert.rejects(discoverPython({ ...environment, CLANKER_PYTHON: path.join(fixture, 'python3.9') }, 'linux'), /CLANKER_PYTHON/);
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
});

// Consume every response, including rejected requests, before testing server shutdown.
function fetch(url, options = {}) {
  return new Promise((resolve, reject) => {
    const body = options.body;
    const req = request(url, {
      method: options.method ?? 'GET',
      headers: { ...options.headers, ...(body ? { 'Content-Length': Buffer.byteLength(body) } : {}) },
      agent: false,
      signal: options.signal,
    }, (res) => {
      let text = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { text += chunk; });
      res.on('error', reject);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, text: async () => text, json: async () => JSON.parse(text) }));
    });
    req.setTimeout(5000, () => req.destroy(new Error('HTTP check timed out')));
    req.on('error', reject);
    req.end(body);
  });
}

function run(...args) {
  return spawnSync(process.execPath, [launcher, ...args], { encoding: 'utf8', timeout: 15000, windowsHide: true });
}

test('help and invalid arguments do not launch a service', () => {
  const help = run('--help');
  assert.equal(help.status, 0, help.stderr);
  assert.match(help.stdout, /dev/);
  assert.doesNotMatch(help.stdout, /--project/);
  const removed = run('start', '--project', 'unused');
  assert.notEqual(removed.status, 0);
  assert.match(removed.stderr, /Unknown option: --project/);
  assert.doesNotMatch(removed.stdout, /Open the local editor:/);
  const bad = run('start', '--not-a-real-flag');
  assert.notEqual(bad.status, 0);
  assert.doesNotMatch(bad.stdout, /Open the local editor:/);
});

test('an explicit missing Python executable fails without fallback', () => {
  const result = spawnSync(process.execPath, [launcher, 'start'], {
    env: { ...process.env, CLANKER_PYTHON: path.join(root, 'missing python executable') },
    encoding: 'utf8', timeout: 15000, windowsHide: true,
  });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr + result.stdout, /Python|CLANKER_PYTHON/);
  assert.doesNotMatch(result.stdout, /Open the local editor:/);
});

test('a checkout without built assets reports the initial build prerequisite', async () => {
  const fixture = await mkdtemp(path.join(tmpdir(), 'clanker missing build '));
  try {
    await mkdir(path.join(fixture, 'routing-editor/scripts'), { recursive: true });
    const copy = path.join(fixture, 'routing-editor/scripts', 'editor.mjs');
    await copyFile(launcher, copy);
    const result = spawnSync(process.execPath, [copy, 'start'], { encoding: 'utf8', timeout: 15000, windowsHide: true });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr + result.stdout, /build|assets|dependencies/i);
    assert.doesNotMatch(result.stdout, /Open the local editor:/);
    await mkdir(path.join(fixture, 'routing-editor/dist'));
    await writeFile(path.join(fixture, 'routing-editor/dist/index.html'), '<div id="root"></div>');
    for (const manifest of ['not-json', JSON.stringify({ schema_version: 999, policy_version: 'unsupported' }), JSON.stringify({ schema_version: 1, policy_version: '5' })]) {
      await writeFile(path.join(fixture, 'routing-editor/dist/compatibility.json'), manifest);
      const incompatible = spawnSync(process.execPath, [copy, 'start'], { encoding: 'utf8', timeout: 15000, windowsHide: true });
      assert.notEqual(incompatible.status, 0);
      assert.match(incompatible.stderr + incompatible.stdout, /incompatible.*build/i);
      assert.doesNotMatch(incompatible.stdout, /Open the local editor:/);
    }
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
});

test('development startup without Node dependencies cleans its Python backend', { timeout: 20000 }, async () => {
  const fixture = await mkdtemp(path.join(tmpdir(), 'clanker missing dependencies '));
  try {
    for (const directory of ['routing-editor/scripts', 'routing-editor/dist', 'subagents/scripts', 'subagents/routing']) {
      await mkdir(path.join(fixture, directory), { recursive: true });
    }
    for (const name of ['routing-editor/scripts/editor.mjs', 'routing-editor/scripts/routing_editor.py', 'routing-editor/scripts/model_discovery.py', 'subagents/scripts/claude_cross_review.py', 'subagents/scripts/routing_policy.py', 'subagents/routing/policy.json']) {
      await copyFile(path.join(root, name), path.join(fixture, name));
    }
    await writeFile(path.join(fixture, 'routing-editor/dist/index.html'), '<div id="root"></div>');
    await writeFile(path.join(fixture, 'routing-editor/dist/compatibility.json'), JSON.stringify({ schema_version: 1, policy_version: '6' }));
    const result = spawnSync(process.execPath, [path.join(fixture, 'routing-editor/scripts/editor.mjs'), 'dev', '--global-config-dir', path.join(fixture, 'prefs')], {
      encoding: 'utf8', timeout: 12000, windowsHide: true,
    });
    assert.equal(result.error, undefined);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr + result.stdout, /dependencies.*unavailable|npm ci/i);
    assert.doesNotMatch(result.stdout, /#token=/);
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
});

async function waitForUrl(child) {
  let output = '';
  let errors = '';
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`Startup timed out: ${errors}`)), 20000);
    child.stderr.on('data', (chunk) => { errors += chunk; });
    child.once('error', (error) => { clearTimeout(timer); reject(error); });
    child.once('exit', (code) => { clearTimeout(timer); reject(new Error(`Exited before readiness (${code}): ${errors}`)); });
    child.stdout.on('data', (chunk) => {
      output += chunk;
      const match = output.match(/Open the local editor: (http:\/\/127\.0\.0\.1:\d+\/#token=[^\s]+)/);
      if (match) { clearTimeout(timer); resolve(new URL(match[1])); }
    });
  });
}

for (const mode of ['start', 'dev']) {
  test(`${mode}: real API, boundary checks, spaced paths and graceful cleanup`, { timeout: 45000 }, async () => {
    const fixture = await mkdtemp(path.join(tmpdir(), 'clanker launcher '));
    const globalDir = path.join(fixture, 'global prefs');
    const project = path.join(fixture, 'project with spaces');
    await mkdir(path.join(project, ".clanker"), { recursive: true });
    const ignored = path.join(project, ".clanker", "orchestration-routing.json");
    await writeFile(ignored, "malformed ignored project preferences");
    let fixtureLauncher = launcher;
    if (mode === 'dev') {
      // Keep a running source-checkout dev server and its dependency cache untouched.
      const checkout = path.join(fixture, 'checkout');
      for (const name of ['routing-editor/scripts/editor.mjs', 'routing-editor/scripts/routing_editor.py', 'routing-editor/scripts/model_discovery.py', 'subagents/scripts/routing_policy.py', 'subagents/scripts/claude_cross_review.py', 'subagents/routing/policy.json', 'routing-editor/index.html', 'routing-editor/package.json']) {
        await mkdir(path.dirname(path.join(checkout, name)), { recursive: true });
        await copyFile(path.join(root, name), path.join(checkout, name));
      }
      for (const name of ['routing-editor/src', 'routing-editor/dist']) {
        await cp(path.join(root, name), path.join(checkout, name), { recursive: true });
      }
      await symlink(path.join(root, 'routing-editor/node_modules'), path.join(checkout, 'routing-editor/node_modules'), process.platform === 'win32' ? 'junction' : 'dir');
      const viteConfig = (await readFile(path.join(root, 'routing-editor/vite.config.ts'), 'utf8'))
        .replace('port: 42069', 'port: 0')
        .replace('export default defineConfig({', `export default defineConfig({ cacheDir: ${JSON.stringify(path.join(checkout, 'vite-cache'))},`);
      await writeFile(path.join(checkout, 'routing-editor/vite.config.ts'), viteConfig);
      fixtureLauncher = path.join(checkout, 'routing-editor/scripts/editor.mjs');
    }
    const child = fork(fixtureLauncher, [mode, '--global-config-dir', 'global prefs'], {
      cwd: fixture, silent: true, windowsHide: true, env: process.env,
    });
    let origin;
    let exited = false;
    child.once('exit', () => { exited = true; });
    try {
      const url = await waitForUrl(child);
      origin = url.origin;
      const token = new URLSearchParams(url.hash.slice(1)).get('token');
      assert.ok(token);
      const headers = { 'X-Clanker-Token': token, Origin: origin, 'Content-Type': 'application/json' };
      const page = await fetch(origin);
      assert.equal(page.status, 200);
      const html = await page.text();
      assert.match(html, /root/);
      assert.ok(html.includes(`name="clanker-session-token" content="${token}"`));
      assert.equal(page.headers['cache-control'], 'no-store');
      assert.equal((await fetch(origin, { headers: { Origin: 'https://example.com' } })).status, 403);
      if (mode === 'dev') {
        assert.ok(Number(url.port) > 0);
        const client = await fetch(`${origin}/@vite/client`);
        assert.equal(client.status, 200);
        assert.match(await client.text(), /WebSocket|HMR/);
        assert.equal((await fetch(`${origin}/src/main.tsx`)).status, 200);
      }
      const configResponse = await fetch(`${origin}/api/config`, { headers });
      assert.equal(configResponse.status, 200);
      const config = await configResponse.json();
      assert.deepEqual(Object.keys(config.scopes), ['global']);
      assert.equal(path.resolve(config.scopes.global.path), path.join(globalDir, 'orchestration-routing.json'));
      assert.equal((await fetch(`${origin}/api/config`)).status, 403);
      assert.equal((await fetch(`${origin}/api/config`, { headers: { ...headers, Origin: 'http://untrusted.example' } })).status, 403);
      assert.equal((await fetch(`${origin}/api/config`, { headers: { ...headers, Host: 'untrusted.example' } })).status, 403);
      assert.equal((await fetch(`${origin}/api/config`, { headers: { ...headers, 'X-Clanker-Token': 'wrong-token' } })).status, 403);
      const document = { schema_version: 1, interactions: { planning: { model: 'gpt-5.6-sol', reasoning: { mode: 'fixed', effort: 'high' } } } };
      const previewBody = JSON.stringify({ scope: 'global', document });
      assert.equal((await fetch(`${origin}/api/preview`, {
        method: 'POST', headers: { 'X-Clanker-Token': token, 'Content-Type': 'application/json' }, body: previewBody,
      })).status, 403);
      assert.equal((await fetch(`${origin}/api/preview`, { method: 'POST', headers, body: previewBody })).status, 200);
      const saved = await fetch(`${origin}/api/save`, {
        method: 'POST', headers, body: JSON.stringify({ scope: 'global', document, revision: config.scopes.global.revision }),
      });
      assert.equal(saved.status, 200, await saved.text());
      assert.deepEqual(JSON.parse(await readFile(path.join(globalDir, 'orchestration-routing.json'), 'utf8')), document);
      assert.equal(await readFile(ignored, 'utf8'), 'malformed ignored project preferences');
    } finally {
      const exit = exited ? Promise.resolve() : once(child, 'exit');
      if (child.connected) child.disconnect();
      let timer;
      try {
        await Promise.race([exit, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Launcher did not stop after IPC parent disconnect')), 8000); })]);
      } finally {
        clearTimeout(timer);
        if (!exited) { child.kill(); await exit; }
        await rm(fixture, { recursive: true, force: true });
      }
    }
    if (origin) await assert.rejects(fetch(origin, { signal: AbortSignal.timeout(1000) }));
  });
}
