/** Unregistered, bounded text-only prompt adapter. No model call or rendering. */
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import { registerHooks, syncBuiltinESMExports } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const SCHEMA = 'archeaxis.openmaic-slide-prompt/v1';
const RESULT = 'archeaxis.openmaic-slide-prompt-result/v1';
const MAX_FRAME = 32768, MAX_REQUEST = 16384, MAX_OUTPUT = 196608;
const NODE_HASH = 'ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32';
const MANIFEST_HASH = '5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3';
const ORIGINALS = {
  'package.json': '5308b268d06dd27e592de00f02d57b046588df0d6e160f4179788388d5a806d1',
  'LICENSE': 'ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19',
  'src/scene-prompts.ts': '06a030bff670868992e37d131fe30e0358304eaa37c4b8f27246560b98a6f1ec',
  'src/prompts/index.ts': '2d71a8c8e261b773562b2d2597d61690fa547a80c7aca9f5cc329b49a6c987ab',
  'src/prompts/loader.ts': '584bd51c71c53c02e058df5209d9bcb1f73ff531677a9d7a3aa168d135a43e50',
  'src/interactive-libraries.ts': '1c9f212d7e2010dd3e1f4889efe22825fcb1f52772b056e5a30fc58753f29de1',
  'templates/slide-content/system.md': 'd0e800d960111e03448d0f0bacdf40acfefcef02bf8e8f9f4f110ba6377d54a1',
  'templates/slide-content/user.md': '7d7486fed0d897a85273794359cd17383d7b9f2dbca7481134a1519687368c99',
  'snippets/slide-image-instructions.md': '00ba082fb8cf2510bcdc6684e09478778c19b5a00bd6e2818208efa55590db0c',
  'snippets/slide-generated-image-instructions.md': 'aed6d0a9ab210562c61183ca29ed7a6635d9c423e8b59a20b59a0d491a8ca0f1',
  'snippets/slide-video-instructions.md': '9a232d6a42e70fc5ac89ec8a8a10420b9c4d5e062287dd3e424e5d9bd934c856',
};
const TEMPLATE_READS = [
  'templates/slide-content/system.md', 'snippets/slide-image-instructions.md',
  'snippets/slide-generated-image-instructions.md', 'snippets/slide-video-instructions.md',
  'templates/slide-content/user.md',
];
const DONOR = path.resolve(fileURLToPath(new URL('./vendor/scene-content-0.3.28-original/generation/', import.meta.url)));
const WORKER = fileURLToPath(import.meta.url);
const sha256 = value => createHash('sha256').update(value).digest('hex');
class Rejection extends Error { constructor(code) { super(code); this.code = code; } }
const reject = code => { throw new Rejection(code); };

// This is identity checking, not a filesystem or process sandbox. Parent
// directories outside DONOR and replacement between verification/import remain.
function readRegular(name, code = 'UPSTREAM_IDENTITY_MISMATCH') {
  let fd;
  try {
    if (!name || name.includes('\\') || name.includes(':') ||
        name.split('/').some(part => !part || part === '.' || part === '..')) reject(code);
    const root = fs.lstatSync(DONOR);
    if (!root.isDirectory() || root.isSymbolicLink()) reject(code);
    const target = path.resolve(DONOR, ...name.split('/'));
    const relative = path.relative(DONOR, target);
    if (!relative || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)) reject(code);
    for (let parent = path.dirname(target); parent !== DONOR; parent = path.dirname(parent)) {
      const info = fs.lstatSync(parent);
      if (!info.isDirectory() || info.isSymbolicLink()) reject(code);
    }
    const before = fs.lstatSync(target);
    if (!before.isFile() || before.isSymbolicLink() || before.nlink !== 1 || before.size > 1_000_000) reject(code);
    fd = fs.openSync(target, 'r');
    const opened = fs.fstatSync(fd);
    if (opened.dev !== before.dev || opened.ino !== before.ino || opened.size !== before.size || opened.nlink !== 1) reject(code);
    // A file can grow after lstat/fstat. Never let readFileSync(fd) allocate
    // against a moving EOF: read at most the observed size plus one byte.
    const buffer = Buffer.allocUnsafe(before.size + 1);
    let length = 0;
    while (length < buffer.length) {
      const count = fs.readSync(fd, buffer, length, Math.min(65_536, buffer.length - length), null);
      if (count === 0) break;
      length += count;
    }
    const data = buffer.subarray(0, length);
    const after = fs.lstatSync(target), final = fs.fstatSync(fd);
    if (data.length !== before.size || after.dev !== opened.dev || after.ino !== opened.ino ||
        after.size !== opened.size || after.nlink !== 1 || final.size !== opened.size) reject(code);
    return data;
  } catch (error) { if (error instanceof Rejection) throw error; reject(code); }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}
function verifyNode() {
  if (process.versions.node !== '24.21.0' || process.execArgv.length || process.argv.length !== 2)
    reject('NODE_IDENTITY_MISMATCH');
  for (const name of ['NODE_OPTIONS', 'NODE_PATH', 'INTERACTIVE_ASSET_BASE_URL'])
    if (Object.hasOwn(process.env, name)) reject('ENVIRONMENT_OVERRIDE');
  let fd;
  try {
    const stat = fs.lstatSync(process.execPath);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size !== 93_580_104) reject('NODE_IDENTITY_MISMATCH');
    fd = fs.openSync(process.execPath, 'r');
    const hash = createHash('sha256'), block = Buffer.allocUnsafe(1024 * 1024);
    let total = 0, count;
    while ((count = fs.readSync(fd, block, 0, block.length, null)) !== 0) {
      total += count; if (total > 93_580_104) reject('NODE_IDENTITY_MISMATCH');
      hash.update(block.subarray(0, count));
    }
    if (total !== 93_580_104 || hash.digest('hex') !== NODE_HASH) reject('NODE_IDENTITY_MISMATCH');
  } catch (error) { if (error instanceof Rejection) throw error; reject('NODE_IDENTITY_MISMATCH'); }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}
function verifyDonor() {
  const manifestBytes = readRegular('ORIGINALS.json');
  if (sha256(manifestBytes) !== MANIFEST_HASH) reject('UPSTREAM_IDENTITY_MISMATCH');
  let manifest;
  try { manifest = JSON.parse(manifestBytes.toString('utf8')); } catch { reject('UPSTREAM_IDENTITY_MISMATCH'); }
  const verified = new Map();
  for (const [name, digest] of Object.entries(ORIGINALS)) {
    const bytes = readRegular(name);
    if (manifest?.originals?.[name] !== digest || sha256(bytes) !== digest) reject('UPSTREAM_IDENTITY_MISMATCH');
    verified.set(name, bytes);
  }
  return verified;
}
function installResolver() {
  const src = name => path.join(DONOR, ...name.split('/'));
  const scene = src('src/scene-prompts.ts'), index = src('src/prompts/index.ts');
  const loader = src('src/prompts/loader.ts'), libs = src('src/interactive-libraries.ts');
  registerHooks({ resolve(specifier, context, nextResolve) {
    const parent = context.parentURL?.startsWith('file:') ? fileURLToPath(context.parentURL) : '';
    let name;
    if (parent === WORKER && specifier === pathToFileURL(scene).href) name = 'src/scene-prompts.ts';
    else if (parent === scene && specifier === './prompts/index.js') name = 'src/prompts/index.ts';
    else if (parent === index && specifier === './loader.js') name = 'src/prompts/loader.ts';
    else if (parent === loader && specifier === '../interactive-libraries.js') name = 'src/interactive-libraries.ts';
    else if (parent === loader && ['node:fs', 'node:path', 'node:url'].includes(specifier)) return nextResolve(specifier, context);
    else reject('UNLISTED_IMPORT');
    if (sha256(readRegular(name)) !== ORIGINALS[name]) reject('UPSTREAM_IDENTITY_MISMATCH');
    return { url: pathToFileURL(src(name)).href, shortCircuit: true };
  } });
  return scene;
}

// Reject duplicate object keys at any depth; JSON.parse alone would keep the last.
function strictJson(bytes) {
  if (bytes.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf]))) reject('INVALID_REQUEST');
  let text, parsed;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes); parsed = JSON.parse(text); }
  catch { reject('INVALID_REQUEST'); }
  let i = 0;
  const ws = () => { while (i < text.length && /[\x20\t\r\n]/.test(text[i])) i++; };
  function string() {
    const start = i++;
    while (i < text.length) {
      if (text[i] === '\\') { i += 2; continue; }
      if (text[i++] === '"') return JSON.parse(text.slice(start, i));
    }
    reject('INVALID_REQUEST');
  }
  function value(depth) {
    if (depth > 64) reject('INVALID_REQUEST');
    ws();
    if (text[i] === '"') { string(); return; }
    if (text[i] === '{') {
      i++; ws(); const seen = new Set();
      if (text[i] === '}') { i++; return; }
      while (i < text.length) {
        ws(); if (text[i] !== '"') reject('INVALID_REQUEST');
        const key = string(); if (seen.has(key)) reject('INVALID_REQUEST'); seen.add(key);
        ws(); if (text[i++] !== ':') reject('INVALID_REQUEST'); value(depth + 1); ws();
        if (text[i] === '}') { i++; return; }
        if (text[i++] !== ',') reject('INVALID_REQUEST');
      }
      reject('INVALID_REQUEST');
    }
    if (text[i] === '[') {
      i++; ws(); if (text[i] === ']') { i++; return; }
      while (i < text.length) {
        value(depth + 1); ws(); if (text[i] === ']') { i++; return; }
        if (text[i++] !== ',') reject('INVALID_REQUEST');
      }
      reject('INVALID_REQUEST');
    }
    const start = i;
    while (i < text.length && !/[\x20\t\r\n,\]}]/.test(text[i])) i++;
    if (start === i) reject('INVALID_REQUEST');
  }
  value(0); ws(); if (i !== text.length) reject('INVALID_REQUEST');
  return parsed;
}
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const exact = (value, names) => object(value) && Object.keys(value).length === names.length && names.every(k => Object.hasOwn(value, k));
const textOk = (value, limit, allowEmpty = false) => typeof value === 'string' && value.isWellFormed() &&
  !value.includes('\0') && Buffer.byteLength(value, 'utf8') <= limit && (allowEmpty || !!value.trim());
function validate(frame) {
  if (!exact(frame, ['schema', 'request_utf8_base64', 'include_private']) || frame.schema !== SCHEMA ||
      typeof frame.include_private !== 'boolean' || typeof frame.request_utf8_base64 !== 'string') reject('INVALID_REQUEST');
  const bytes = Buffer.from(frame.request_utf8_base64, 'base64');
  if (bytes.length > MAX_REQUEST || bytes.toString('base64') !== frame.request_utf8_base64) reject('INVALID_REQUEST');
  const request = strictJson(bytes);
  if (!exact(request, ['outline', 'language_directive']) || !exact(request.outline, ['title', 'description', 'key_points']) ||
      !textOk(request.outline.title, 1024) || !textOk(request.outline.description, 6000, true) ||
      !textOk(request.language_directive, 2000, true) || !Array.isArray(request.outline.key_points) ||
      request.outline.key_points.length > 20 || !request.outline.key_points.every(p => textOk(p, 512))) reject('INVALID_REQUEST');
  return request;
}
function fixed(status) {
  return { schema: RESULT, status, scope: 'CALLER_SUPPLIED_UNVERIFIED',
    operation: 'UPSTREAM_SLIDE_PROMPT_ONLY', model_call: 'NOT_INVOKED',
    full_generation: 'NOT_PERFORMED', core_authorization: 'NOT_ESTABLISHED',
    resource_availability: 'NOT_VERIFIED', network_isolation: 'NOT_ESTABLISHED', private: null };
}
async function main() {
  verifyNode();
  let size = 0; const chunks = [];
  for await (const chunk of process.stdin) {
    size += chunk.length; if (size > MAX_FRAME) reject('INPUT_TOO_LARGE'); chunks.push(chunk);
  }
  const frame = strictJson(Buffer.concat(chunks));
  const request = validate(frame), files = verifyDonor();
  const scene = installResolver();
  const { buildSlideContentPrompt } = await import(pathToFileURL(scene).href);
  if (typeof buildSlideContentPrompt !== 'function') reject('UNEXPECTED_UPSTREAM_RESULT');
  const seen = [], oldRead = fs.readFileSync;
  let prompt;
  try {
    // Only the original loader's five exact files are served from verified
    // buffers during the synchronous call; this is not an OS I/O sandbox.
    fs.readFileSync = function (name, encoding) {
      if (typeof name !== 'string' || encoding !== 'utf-8') reject('UNLISTED_TEMPLATE_READ');
      const rel = path.relative(DONOR, path.resolve(name)).split(path.sep).join('/');
      if (!TEMPLATE_READS.includes(rel)) reject('UNLISTED_TEMPLATE_READ');
      seen.push(rel); return files.get(rel).toString('utf8');
    };
    syncBuiltinESMExports();
    prompt = buildSlideContentPrompt(
      { imageElementEnabled: false, generatedImageEnabled: false, generatedVideoEnabled: false },
      { title: request.outline.title, description: request.outline.description,
        keyPoints: request.outline.key_points.map((p, i) => `${i + 1}. ${p}`).join('\n'),
        elements: '（根据要点自动生成）', assignedImages: '无可用图片，禁止插入任何 image 元素',
        teacherContext: '', languageDirective: request.language_directive });
  } finally { fs.readFileSync = oldRead; syncBuiltinESMExports(); }
  if (JSON.stringify(seen) !== JSON.stringify(TEMPLATE_READS) || !exact(prompt, ['system', 'user']) ||
      typeof prompt.system !== 'string' || typeof prompt.user !== 'string' ||
      Buffer.byteLength(prompt.system, 'utf8') > 65536 || Buffer.byteLength(prompt.user, 'utf8') > 32768)
    reject('UNEXPECTED_UPSTREAM_RESULT');
  const out = fixed('BUILT');
  if (frame.include_private) out.private = { system: prompt.system, user: prompt.user,
    system_sha256: sha256(Buffer.from(prompt.system, 'utf8')), user_sha256: sha256(Buffer.from(prompt.user, 'utf8')) };
  return out;
}
try {
  const result = await main();
  const output = JSON.stringify(result);
  if (Buffer.byteLength(output, 'utf8') + 1 > MAX_OUTPUT) reject('OUTPUT_TOO_LARGE');
  process.stdout.write(output + '\n');
} catch (error) {
  const out = fixed('REJECTED'); out.error_code = error instanceof Rejection ? error.code : 'INTERNAL_FAILURE';
  process.stdout.write(JSON.stringify(out) + '\n');
}
