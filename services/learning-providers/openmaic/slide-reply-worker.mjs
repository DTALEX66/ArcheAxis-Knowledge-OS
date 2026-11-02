/** Unregistered text-element response candidate; no model, scene, Core or rendering. */
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import { registerHooks } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const SCHEMA = 'archeaxis.openmaic-slide-reply/v1';
const RESULT = 'archeaxis.openmaic-slide-reply-result/v1';
const MAX_FRAME = 32768, MAX_REPLY = 16384, MAX_OUTPUT = 196608;
const NODE_HASH = 'ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32';
const GEN_MANIFEST = '5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3';
const DSL_MANIFEST = 'c7564a5741c0807834ebcf77779a50590b927fa8b7e93f49494d1ef8eac6c317';
const NPM_MANIFEST = '11533c9ff27380455269407795ca6dd72a9c997ae4b4efa0285110ac23e60453';
const GEN = {
  'package.json': '5308b268d06dd27e592de00f02d57b046588df0d6e160f4179788388d5a806d1',
  'LICENSE': 'ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19',
  'src/json-repair.ts': 'dd0cfb6b1224e28c0e96ac5437e06074f5159ab5ec2cb93d4c81784bafcbedff',
  'src/logger.ts': 'f8fd9136c2d5a31881c7c00d8a1f1804ba04af5f9d76c85888296e2d0b481306',
};
const DSL = {
  'package.json': '847c2f4054034aab29586171872cb64a0f0b4e39db8dd9b8c50cff5e67014c98',
  'LICENSE': 'ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19',
  'src/normalize.ts': 'e4f21f3273d9d65dadd53768afc5049b5473d087d1c525ea804c3d057b5ecf06',
  'src/stage.ts': 'b8ce1ac2cff5a37e7fee7b23a1eb4df59499f0357366d80166163d7b32a9fc6a',
};
const NPM = {
  'LICENSE.md': 'fd50f5abb7eeb614c8d1293b9f239a5238d7536e3a9a9a8929a082c82d12b3fd',
  'package.json': '34af00e07186a9ca212bd1065572bbc8d961937728f1a32551ed9016e0e01f41',
  'lib/esm/index.js': '523d175b61d8517fd3ba90cd2f065c6ecd45f4c95ea7ac706a9d87ccaceb7faf',
  'lib/esm/regular/jsonrepair.js': '9b7d7367a763931855d1c962e998529f06c6e80a4a056dccb8ebdb96e1d68a1d',
  'lib/esm/utils/JSONRepairError.js': '760bbdf77243afe6da53aad48520423c2b3da2e15838ca89cb118e87067ef130',
  'lib/esm/utils/stringUtils.js': 'd5e1065bc473e1c06c9ae2c70dae048175fe8b96c7749b00c267fe29f5c322c3',
};
const service = path.dirname(fileURLToPath(import.meta.url));
const roots = {
  gen: path.join(service, 'vendor/scene-content-0.3.28-original/generation'),
  dsl: path.join(service, 'vendor/scene-content-0.3.28-original/dsl'),
  npm: path.join(service, 'vendor/npm/jsonrepair-3.13.3'),
};
const worker = fileURLToPath(import.meta.url);
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
class Refusal extends Error { constructor(code) { super(code); this.code = code; } }
const reject = code => { throw new Refusal(code); };
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const keys = (v, required, optional = []) => object(v) && required.every(k => Object.hasOwn(v, k)) &&
  Object.keys(v).every(k => required.includes(k) || optional.includes(k));

// Bounded identity checks reduce drift but do not lock paths across import.
function readMember(root, name) {
  let fd;
  try {
    if (!name || name.includes('\\') || name.includes(':') || name.split('/').some(p => !p || p === '.' || p === '..'))
      reject('SOURCE_IDENTITY_MISMATCH');
    let directory = root;
    if (!fs.lstatSync(directory).isDirectory() || fs.lstatSync(directory).isSymbolicLink()) reject('SOURCE_IDENTITY_MISMATCH');
    const pieces = name.split('/');
    for (const part of pieces.slice(0, -1)) {
      directory = path.join(directory, part); const stat = fs.lstatSync(directory);
      if (!stat.isDirectory() || stat.isSymbolicLink()) reject('SOURCE_IDENTITY_MISMATCH');
    }
    const file = path.join(directory, pieces.at(-1));
    const before = fs.lstatSync(file);
    if (!before.isFile() || before.isSymbolicLink() || before.nlink !== 1 || before.size > 1_000_000)
      reject('SOURCE_IDENTITY_MISMATCH');
    fd = fs.openSync(file, 'r'); const opened = fs.fstatSync(fd);
    if (opened.dev !== before.dev || opened.ino !== before.ino || opened.size !== before.size || opened.nlink !== 1)
      reject('SOURCE_IDENTITY_MISMATCH');
    const bytes = Buffer.allocUnsafe(before.size + 1); let total = 0;
    while (total < bytes.length) {
      const count = fs.readSync(fd, bytes, total, Math.min(65536, bytes.length - total), null);
      if (!count) break; total += count;
    }
    const after = fs.lstatSync(file), final = fs.fstatSync(fd);
    if (total !== before.size || after.dev !== opened.dev || after.ino !== opened.ino ||
        after.nlink !== 1 || after.size !== opened.size || final.size !== opened.size) reject('SOURCE_IDENTITY_MISMATCH');
    return bytes.subarray(0, total);
  } catch (error) { if (error instanceof Refusal) throw error; reject('SOURCE_IDENTITY_MISMATCH'); }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}
function verifyNode() {
  if (process.versions.node !== '24.21.0' || process.execArgv.length || process.argv.length !== 2)
    reject('NODE_IDENTITY_MISMATCH');
  if (Object.hasOwn(process.env, 'NODE_OPTIONS') || Object.hasOwn(process.env, 'NODE_PATH')) reject('ENVIRONMENT_OVERRIDE');
  let fd;
  try {
    const stat = fs.lstatSync(process.execPath);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size !== 93_580_104) reject('NODE_IDENTITY_MISMATCH');
    fd = fs.openSync(process.execPath, 'r'); const hash = createHash('sha256'), buffer = Buffer.allocUnsafe(1024 * 1024);
    let total = 0, count;
    while ((count = fs.readSync(fd, buffer, 0, buffer.length, null)) !== 0) {
      total += count; if (total > 93_580_104) reject('NODE_IDENTITY_MISMATCH'); hash.update(buffer.subarray(0, count));
    }
    if (total !== 93_580_104 || hash.digest('hex') !== NODE_HASH) reject('NODE_IDENTITY_MISMATCH');
  } catch (error) { if (error instanceof Refusal) throw error; reject('NODE_IDENTITY_MISMATCH'); }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}
function verifySource(root, manifestName, manifestHash, expected, field) {
  const manifestBytes = readMember(root, manifestName);
  if (sha256(manifestBytes) !== manifestHash) reject('SOURCE_IDENTITY_MISMATCH');
  let manifest; try { manifest = JSON.parse(manifestBytes.toString('utf8')); } catch { reject('SOURCE_IDENTITY_MISMATCH'); }
  for (const [name, hash] of Object.entries(expected)) {
    const recorded = field === 'originals' ? manifest?.originals?.[name] : manifest?.files?.[name]?.sha256;
    if (recorded !== hash || sha256(readMember(root, name)) !== hash) reject('SOURCE_IDENTITY_MISMATCH');
  }
}
function file(root, name) { return pathToFileURL(path.join(root, ...name.split('/'))).href; }
function installResolver() {
  const gen = name => file(roots.gen, name), dsl = name => file(roots.dsl, name), npm = name => file(roots.npm, name);
  const routes = new Map([
    [`${pathToFileURL(worker).href}|${gen('src/json-repair.ts')}`, [roots.gen, 'src/json-repair.ts', GEN]],
    [`${pathToFileURL(worker).href}|${dsl('src/normalize.ts')}`, [roots.dsl, 'src/normalize.ts', DSL]],
    [`${gen('src/json-repair.ts')}|./logger.js`, [roots.gen, 'src/logger.ts', GEN]],
    [`${gen('src/json-repair.ts')}|jsonrepair`, [roots.npm, 'lib/esm/index.js', NPM]],
    [`${dsl('src/normalize.ts')}|./stage.js`, [roots.dsl, 'src/stage.ts', DSL]],
    [`${npm('lib/esm/index.js')}|./regular/jsonrepair.js`, [roots.npm, 'lib/esm/regular/jsonrepair.js', NPM]],
    [`${npm('lib/esm/index.js')}|./utils/JSONRepairError.js`, [roots.npm, 'lib/esm/utils/JSONRepairError.js', NPM]],
    [`${npm('lib/esm/regular/jsonrepair.js')}|../utils/JSONRepairError.js`, [roots.npm, 'lib/esm/utils/JSONRepairError.js', NPM]],
    [`${npm('lib/esm/regular/jsonrepair.js')}|../utils/stringUtils.js`, [roots.npm, 'lib/esm/utils/stringUtils.js', NPM]],
  ]);
  registerHooks({ resolve(specifier, context) {
    const target = routes.get(`${context.parentURL}|${specifier}`);
    if (!target) reject('UNLISTED_IMPORT');
    const [root, name, expected] = target;
    if (sha256(readMember(root, name)) !== expected[name]) reject('SOURCE_IDENTITY_MISMATCH');
    return { url: file(root, name), shortCircuit: true };
  } });
  return { parser: gen('src/json-repair.ts'), normalizer: dsl('src/normalize.ts') };
}

// JSON.parse accepts duplicate names and rounds numbers. This scanner runs
// after JSON.parse and conservatively requires canonical ECMAScript numbers.
function strictJson(bytes, code) {
  if (bytes.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf]))) reject(code);
  let text, parsed;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes); parsed = JSON.parse(text); } catch { reject(code); }
  let i = 0;
  const ws = () => { while (i < text.length && /[\x20\t\r\n]/.test(text[i])) i++; };
  function str() {
    const start = i++;
    while (i < text.length) {
      if (text[i] === '\\') { i += 2; continue; }
      if (text[i++] === '"') return JSON.parse(text.slice(start, i));
    }
    reject(code);
  }
  function value(depth) {
    if (depth > 64) reject(code); ws();
    if (text[i] === '"') { str(); return; }
    if (text[i] === '{') {
      i++; ws(); const seen = new Set(); if (text[i] === '}') { i++; return; }
      while (i < text.length) {
        ws(); if (text[i] !== '"') reject(code); const key = str(); if (seen.has(key)) reject(code); seen.add(key);
        ws(); if (text[i++] !== ':') reject(code); value(depth + 1); ws();
        if (text[i] === '}') { i++; return; } if (text[i++] !== ',') reject(code);
      } reject(code);
    }
    if (text[i] === '[') {
      i++; ws(); if (text[i] === ']') { i++; return; }
      while (i < text.length) {
        value(depth + 1); ws(); if (text[i] === ']') { i++; return; } if (text[i++] !== ',') reject(code);
      } reject(code);
    }
    const start = i; while (i < text.length && !/[\x20\t\r\n,\]}]/.test(text[i])) i++;
    const token = text.slice(start, i); if (!token) reject(code);
    if (/^-?\d/.test(token) && (!Number.isFinite(Number(token)) || JSON.stringify(Number(token)) !== token)) reject(code);
  }
  value(0); ws(); if (i !== text.length) reject(code); return parsed;
}
function serializable(value, depth = 0) {
  if (depth > 64) return false;
  if (value === null || typeof value === 'boolean') return true;
  if (typeof value === 'string') return value.isWellFormed();
  if (typeof value === 'number') return Number.isFinite(value) && !Object.is(value, -0);
  if (Array.isArray(value)) return value.every(v => serializable(v, depth + 1));
  return object(value) && Object.keys(value).every(k => k.isWellFormed() && serializable(value[k], depth + 1));
}
function same(a, b) {
  if (Object.is(a, b)) return true;
  if (Array.isArray(a) || Array.isArray(b)) return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((v, i) => same(v, b[i]));
  if (!object(a) || !object(b)) return false;
  return Object.keys(a).length === Object.keys(b).length && Object.keys(a).every(k => Object.hasOwn(b, k) && same(a[k], b[k]));
}
const text = (v, max, empty = false) => typeof v === 'string' && v.isWellFormed() && !v.includes('\0') &&
  Buffer.byteLength(v, 'utf8') <= max && (empty || !!v.trim());
const color = v => typeof v === 'string' && (/^#(?:[a-f\d]{3}|[a-f\d]{4}|[a-f\d]{6}|[a-f\d]{8})$/i.test(v) || /^[a-z]{1,24}$/i.test(v));
const finite = (v, lo, hi) => typeof v === 'number' && Number.isFinite(v) && v >= lo && v <= hi;
function supported(value) {
  if (!keys(value, ['elements'], ['background', 'remark']) || !Array.isArray(value.elements) ||
      value.elements.length < 1 || value.elements.length > 200) return false;
  if (Object.hasOwn(value, 'remark') && !text(value.remark, 8000)) return false;
  if (Object.hasOwn(value, 'background') && (!keys(value.background, ['type', 'color']) ||
      value.background.type !== 'solid' || !color(value.background.color))) return false;
  const ids = new Set();
  for (const e of value.elements) {
    if (!keys(e, ['type', 'left', 'top', 'width', 'height', 'rotate', 'content'], ['id', 'defaultFontName', 'defaultColor']) ||
        e.type !== 'text' || !finite(e.left, -10000, 10000) || !finite(e.top, -10000, 10000) ||
        !finite(e.width, 0.01, 10000) || !finite(e.height, 0.01, 10000) || e.rotate !== 0 || !text(e.content, 16000)) return false;
    if (Object.hasOwn(e, 'id')) {
      if (typeof e.id !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(e.id) || ids.has(e.id)) return false;
      ids.add(e.id);
    }
    if (Object.hasOwn(e, 'defaultFontName') && !text(e.defaultFontName, 240, true)) return false;
    if (Object.hasOwn(e, 'defaultColor') && e.defaultColor !== '' && !color(e.defaultColor)) return false;
  }
  return true;
}
function allowedChanges(before, after) {
  const expected = structuredClone(before), changes = [];
  for (let i = 0; i < expected.elements.length; i++) {
    const e = expected.elements[i];
    for (const [field, fallback] of [['defaultFontName', 'Microsoft YaHei'], ['defaultColor', '#333333']]) {
      if (!Object.hasOwn(e, field) || e[field] === '') {
        changes.push({ path: `/elements/${i}/${field}`, kind: Object.hasOwn(e, field) ? 'EMPTY_REPLACED_WITH_DEFAULT' : 'ABSENT_FILLED_WITH_DEFAULT' });
        e[field] = fallback;
      }
    }
  }
  if (!same(expected, after)) reject('UNEXPECTED_UPSTREAM_CHANGE');
  return changes;
}
function blob(bytes) { return { utf8_base64: bytes.toString('base64'), bytes: bytes.length, sha256: sha256(bytes) }; }
function envelope(status, code) {
  return { schema: RESULT, status, reason: code, scope: 'CALLER_SUPPLIED_UNVERIFIED',
    model_call: 'NOT_INVOKED', full_scene_generation: 'NOT_PERFORMED', core_authorization: 'NOT_ESTABLISHED',
    canonical_persistence: 'NOT_PERFORMED', rendering: 'NOT_PERFORMED', sanitization: 'NOT_PERFORMED',
    content_trust: 'UNTRUSTED', network_isolation: 'NOT_ESTABLISHED', private: null };
}
async function main() {
  verifyNode(); let total = 0; const chunks = [];
  for await (const chunk of process.stdin) { total += chunk.length; if (total > MAX_FRAME) reject('INPUT_TOO_LARGE'); chunks.push(chunk); }
  const frame = strictJson(Buffer.concat(chunks), 'INVALID_REQUEST');
  if (!keys(frame, ['schema', 'reply_utf8_base64', 'include_private']) || frame.schema !== SCHEMA ||
      typeof frame.include_private !== 'boolean' || typeof frame.reply_utf8_base64 !== 'string') reject('INVALID_REQUEST');
  const raw = Buffer.from(frame.reply_utf8_base64, 'base64');
  if (!raw.length || raw.length > MAX_REPLY || raw.toString('base64') !== frame.reply_utf8_base64) reject('INVALID_REQUEST');
  let response;
  try { response = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(raw); }
  catch {
    const out = envelope('QUARANTINED', 'INVALID_REPLY_UTF8');
    if (frame.include_private) out.private = { reply: blob(raw), upstream_observation: 'NOT_INVOKED' };
    return out;
  }
  verifySource(roots.gen, 'ORIGINALS.json', GEN_MANIFEST, GEN, 'originals');
  verifySource(roots.dsl, 'ORIGINALS.json', DSL_MANIFEST, DSL, 'originals');
  verifySource(roots.npm, 'SOURCE.json', NPM_MANIFEST, NPM, 'files');
  const modules = installResolver();
  const { parseJsonResponse } = await import(modules.parser);
  const { normalizeElement } = await import(modules.normalizer);
  if (typeof parseJsonResponse !== 'function' || typeof normalizeElement !== 'function') reject('UNEXPECTED_UPSTREAM_RESULT');
  const counts = { debug: 0, info: 0, warn: 0, error: 0 };
  // Original logger arguments can include source excerpts; only counts survive.
  const logger = Object.fromEntries(Object.keys(counts).map(k => [k, () => { counts[k]++; }]));
  let parsed, parserFailed = false;
  try { parsed = parseJsonResponse(response, { logger }); } catch { parserFailed = true; }
  let observation = { state: parserFailed ? 'UPSTREAM_THROW' : parsed === null ? 'UPSTREAM_NULL' : 'UNREPRESENTABLE' };
  if (!parserFailed && parsed !== null && serializable(parsed)) {
    const bytes = Buffer.from(JSON.stringify(parsed), 'utf8');
    if (bytes.length <= 32768) observation = { state: 'SERIALIZED_UPSTREAM_VALUE', value: blob(bytes) };
  }
  const privateBase = { reply: blob(raw), upstream_observation: observation, diagnostic_counts: counts };
  const quarantine = reason => { const out = envelope('QUARANTINED', reason); if (frame.include_private) out.private = privateBase; return out; };
  if (parserFailed) return quarantine('UPSTREAM_FAILURE');
  if (parsed === null) return quarantine('UPSTREAM_NULL');
  let exact;
  try { exact = strictJson(raw, 'NONEXACT_OR_AMBIGUOUS_JSON'); } catch { return quarantine('NONEXACT_OR_AMBIGUOUS_JSON'); }
  if (!serializable(exact) || !serializable(parsed) || !same(exact, parsed)) return quarantine('UPSTREAM_PROJECTION_MISMATCH');
  if (!supported(exact)) return quarantine('UNSUPPORTED_SLIDE_REPLY');
  const original = structuredClone(exact);
  let elements;
  try { elements = exact.elements.map(e => normalizeElement(e)); } catch { return quarantine('UPSTREAM_NORMALIZATION_FAILURE'); }
  if (!same(exact, original)) return quarantine('UPSTREAM_MUTATED_INPUT');
  const normalized = { ...exact, elements };
  if (!supported(normalized)) return quarantine('UNEXPECTED_UPSTREAM_RESULT');
  let changes;
  try { changes = allowedChanges(original, normalized); } catch { return quarantine('UNEXPECTED_UPSTREAM_CHANGE'); }
  const normalizedBytes = Buffer.from(JSON.stringify(normalized), 'utf8');
  const out = envelope('CANDIDATE', 'EXACT_TEXT_ELEMENTS_ONLY');
  if (frame.include_private) out.private = { ...privateBase, normalized: blob(normalizedBytes), semantic_changes: changes };
  return out;
}
try {
  const result = await main(); const output = JSON.stringify(result) + '\n';
  if (Buffer.byteLength(output, 'utf8') > MAX_OUTPUT) reject('OUTPUT_TOO_LARGE');
  process.stdout.write(output);
} catch (error) {
  process.stdout.write(JSON.stringify(envelope('REJECTED', error instanceof Refusal ? error.code : 'INTERNAL_FAILURE')) + '\n');
}
