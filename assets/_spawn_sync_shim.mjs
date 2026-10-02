// Drop-in replacement for Node's execFileSync.
//
// This sandbox blocks synchronous process creation (spawnSync / execFileSync)
// for every executable (they fail with errno -4082 EBUSY), while asynchronous
// `spawn` works fine. To keep the project's synchronous call sites untouched,
// this shim re-implements execFileSync on top of async `spawn`:
//   - the child is launched via `cmd.exe /c <tmp>.cmd`, which redirects the
//     inner command's stdout/stderr to files and writes its exit code to a
//     sentinel file on completion;
//   - the parent blocks the calling thread with Atomics.wait (no event loop
//     needed) until the sentinel appears, then reads the captured output.
// The child is a fully independent OS process, so it runs to completion even
// while the parent thread is blocked.

import {spawn} from 'node:child_process';
import {
  openSync,
  readFileSync,
  writeFileSync,
  existsSync,
  mkdtempSync,
  rmSync,
} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const _sab = new Int32Array(new SharedArrayBuffer(4));
const sleepSync = (ms) => {
  try {
    Atomics.wait(_sab, 0, 0, ms);
  } catch {
    // SharedArrayBuffer unavailable (very old engine) — fall back to a tiny
    // busy spin is not ideal, but this path is effectively unreachable here.
  }
};

const quoteArg = (value) => {
  const s = String(value);
  // Windows cmd argument quoting: wrap in double quotes, double internal ".
  return `"${s.replace(/"/g, '""')}"`;
};

export function execFileSyncShim(file, args = [], options = {}) {
  const encoding = options.encoding || null;
  const cwd = options.cwd;
  const env = options.env || process.env;
  const timeout = options.timeout || 0;

  const dir = mkdtempSync(join(tmpdir(), 'exs-'));
  const outPath = join(dir, 'stdout.bin');
  const errPath = join(dir, 'stderr.txt');
  const codePath = join(dir, 'code.txt');
  const cmdPath = join(dir, 'run.cmd');

  const inner = [file, ...(args || [])].map(quoteArg).join(' ');
  const bat = `@echo off\r\n${inner} > "${outPath}" 2> "${errPath}"\r\necho %ERRORLEVEL% > "${codePath}"\r\n`;
  writeFileSync(cmdPath, bat);

  let child;
  try {
    child = spawn('cmd.exe', ['/d', '/c', cmdPath], {
      cwd,
      env,
      windowsHide: true,
      stdio: 'ignore',
    });
  } catch (e) {
    cleanup(dir);
    throw e;
  }

  const start = Date.now();
  while (!existsSync(codePath)) {
    sleepSync(20);
    if (timeout && Date.now() - start > timeout) {
      try {
        child.kill('SIGKILL');
      } catch {
        /* ignore */
      }
      cleanup(dir);
      const err = new Error(
        `execFileSyncShim timed out after ${timeout}ms: ${file} ${(args || []).join(' ')}`,
      );
      err.code = 'ETIMEDOUT';
      throw err;
    }
  }

  let code = -1;
  try {
    code = Number(readFileSync(codePath, 'utf8').trim());
  } catch {
    code = -1;
  }

  let stdout;
  try {
    stdout = readFileSync(outPath, encoding === 'utf8' ? 'utf8' : null);
  } catch {
    stdout = encoding === 'utf8' ? '' : Buffer.alloc(0);
  }
  let stderr;
  try {
    stderr = readFileSync(errPath, 'utf8');
  } catch {
    stderr = '';
  }

  cleanup(dir);

  if (code !== 0) {
    const err = new Error(
      `Command failed: ${file} ${(args || []).join(' ')}\n${stderr}`,
    );
    err.code = code;
    err.status = code;
    err.stderr = stderr;
    err.stdout = typeof stdout === 'string' ? stdout : stdout.toString('utf8');
    throw err;
  }
  return stdout;
}

function cleanup(dir) {
  try {
    rmSync(dir, {recursive: true, force: true});
  } catch {
    /* best-effort */
  }
}
