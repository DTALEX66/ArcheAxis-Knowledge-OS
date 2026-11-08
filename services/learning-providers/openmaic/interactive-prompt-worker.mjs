/** Unregistered, bounded prompt adapter for the original interactive widget prompts.
 *
 * It renders the donor SOLID/DIAGRAM/CODE/GAME/3D-VISUALIZATION content prompt
 * for one outline and returns it only to the calling host. No model call, no
 * HTML, no rendering, no persistence and no Core authorization happen here.
 */
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import { registerHooks, syncBuiltinESMExports } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const SCHEMA = 'archeaxis.openmaic-interactive-prompt/v1';
const RESULT = 'archeaxis.openmaic-interactive-prompt-result/v1';
const MAX_FRAME = 32768, MAX_REQUEST = 16384, MAX_OUTPUT = 196608;
const NODE_HASH = 'ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32';
const MANIFEST_HASH = '5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3';
const ORIGINALS = {
  'package.json': '5308b268d06dd27e592de00f02d57b046588df0d6e160f4179788388d5a806d1',
  'LICENSE': 'ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19',
  'src/prompts/index.ts': '2d71a8c8e261b773562b2d2597d61690fa547a80c7aca9f5cc329b49a6c987ab',
  'src/prompts/loader.ts': '584bd51c71c53c02e058df5209d9bcb1f73ff531677a9d7a3aa168d135a43e50',
  'src/interactive-libraries.ts': '1c9f212d7e2010dd3e1f4889efe22825fcb1f52772b056e5a30fc58753f29de1',
};
// One prompt directory per widget type; each system template includes the same
// three snippets. Anything else read through the patched loader is refused.
const TEMPLATES = {
  simulation: 'simulation-content', diagram: 'diagram-content', code: 'code-content',
  game: 'game-content', visualization3d: 'visualization3d-content',
};
const SNIPPETS = ['interactive-libraries', 'interactive-math', 'interactive-observation'];
const WIDEN = ['simulation', 'diagram', 'code', 'game', 'visualization3d'];
const DONOR = path.resolve(fileURLToPath(new URL('./vendor/scene-content-0.3.28-original/generation/', import.meta.url)));
const WORKER = fileURLToPath(import.meta.url);
const sha256 = value => createHash('sha256').update(value).digest('hex');
class Rejection extends Error { constructor(code) { super(code); this.code = code; } }
const reject = code => { throw new Rejection(code); };

// Identity checking, not a filesystem or process sandbox: parents outside DONOR
// and replacement between verification and import remain unchecked.
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
    // Bound the read at the observed size plus one byte so a growing file
    // cannot make readFileSync(fd) allocate against a moving EOF.
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
  for (const directory of Object.values(TEMPLATES)) {
    for (const file of [`templates/${directory}/system.md`, `templates/${directory}/user.md`]) {
      const bytes = readRegular(file);
      if (manifest?.originals?.[file] !== sha256(bytes)) reject('UPSTREAM_IDENTITY_MISMATCH');
      verified.set(file, bytes);
    }
  }
  for (const snippet of SNIPPETS) {
    const file = `snippets/${snippet}.md`;
    const bytes = readRegular(file);
    if (manifest?.originals?.[file] !== sha256(bytes)) reject('UPSTREAM_IDENTITY_MISMATCH');
    verified.set(file, bytes);
  }
  return verified;
}
function installResolver() {
  const src = name => path.join(DONOR, ...name.split('/'));
  const index = src('src/prompts/index.ts'), loader = src('src/prompts/loader.ts');
  const libs = src('src/interactive-libraries.ts');
  const fileUrl = name => pathToFileURL(src(name)).href;
  registerHooks({ resolve(specifier, context, nextResolve) {
    const parent = context.parentURL?.startsWith('file:') ? fileURLToPath(context.parentURL) : '';
    let name;
    if (parent === WORKER && specifier === fileUrl('src/prompts/index.ts')) name = 'src/prompts/index.ts';
    else if (parent === index && specifier === './loader.js') name = 'src/prompts/loader.ts';
    else if (parent === loader && specifier === '../interactive-libraries.js') name = 'src/interactive-libraries.ts';
    else if (parent === loader && ['node:fs', 'node:path', 'node:url'].includes(specifier)) return nextResolve(specifier, context);
    else reject('UNLISTED_IMPORT');
    if (sha256(readRegular(name)) !== ORIGINALS[name]) reject('UPSTREAM_IDENTITY_MISMATCH');
    return { url: fileUrl(name), shortCircuit: true };
  } });
  return index;
}

// Reject duplicate object keys at any depth; JSON.parse alone keeps the last.
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
const stringsOk = (value, count, limit) => Array.isArray(value) && value.length <= count &&
  value.every(item => textOk(item, limit));
function widgetOutlineOk(widget, outline) {
  if (widget === undefined) return true;
  const keys = { simulation: ['concept', 'key_variables'], diagram: ['diagram_type', 'node_count', 'nodes'],
    code: ['language', 'challenge_type'], game: ['game_type', 'challenge', 'player_controls', 'physics_concept'],
    visualization3d: ['visualization_type', 'objects', 'interactions'] }[outline];
  if (!object(widget) || Object.keys(widget).some(key => !keys.includes(key))) return false;
  for (const key of Object.keys(widget)) {
    const value = widget[key];
    if (key === 'node_count') {
      if (typeof value !== 'number' || !Number.isInteger(value) || value < 0 || value > 200) return false;
    } else if (key === 'nodes' || key === 'objects' || key === 'interactions' || key === 'key_variables' || key === 'player_controls') {
      if (!stringsOk(value, 64, 512)) return false;
    } else if (!textOk(value, 512, true)) return false;
  }
  return true;
}
function validate(frame) {
  if (!exact(frame, ['schema', 'request_utf8_base64', 'include_private']) || frame.schema !== SCHEMA ||
      typeof frame.include_private !== 'boolean' || typeof frame.request_utf8_base64 !== 'string') reject('INVALID_REQUEST');
  const bytes = Buffer.from(frame.request_utf8_base64, 'base64');
  if (bytes.length > MAX_REQUEST || bytes.toString('base64') !== frame.request_utf8_base64) reject('INVALID_REQUEST');
  const request = strictJson(bytes);
  if (!exact(request, ['outline', 'language_directive']) ||
      !exact(request.outline, ['title', 'description', 'key_points', 'widget_type', 'widget_outline']) ||
      !textOk(request.outline.title, 1024) || !textOk(request.outline.description, 6000, true) ||
      !textOk(request.language_directive, 2000, true) || !stringsOk(request.outline.key_points, 20, 512) ||
      typeof request.outline.widget_type !== 'string') reject('INVALID_REQUEST');
  // Procedural skill needs the donor's explicit allow flag; this adapter leaves
  // it out on purpose instead of silently enabling the operation-checklist path.
  if (!WIDEN.includes(request.outline.widget_type)) reject('UNSUPPORTED_WIDGET_TYPE');
  if (!widgetOutlineOk(request.outline.widget_outline, request.outline.widget_type)) reject('INVALID_REQUEST');
  return request;
}
function variablesFor(outline, languageDirective) {
  const widget = outline.widget_outline ?? {};
  const keyPoints = outline.key_points.join('\n');
  // The donor templates have no dedicated placeholders for these admitted
  // details. Carry them into their existing description slot instead of
  // silently discarding them or changing the byte-preserved templates.
  const descriptionWith = details => [outline.description, ...details].filter(Boolean).join('\n');
  switch (outline.widget_type) {
    case 'simulation':
      return { conceptName: widget.concept || outline.title, conceptOverview: outline.description,
        keyPoints, variables: (widget.key_variables || []).join(', '), designIdea: '', languageDirective };
    case 'diagram': {
      const prescribedNodes = widget.nodes ?? [];
      return { title: outline.title, diagramType: widget.diagram_type || 'flowchart',
        description: outline.description, keyPoints, nodeCount: widget.node_count ?? prescribedNodes.length,
        prescribedNodes, hasNodeCount: typeof widget.node_count === 'number' && widget.node_count > 0,
        hasPrescribedNodes: prescribedNodes.length > 0, languageDirective };
    }
    case 'code':
      return { title: outline.title, programmingLanguage: widget.language || 'python',
        description: descriptionWith([widget.challenge_type && `Challenge type: ${widget.challenge_type}`]),
        keyPoints, starterCode: '', testCases: '', hints: '', languageDirective };
    case 'game':
      return { title: outline.title, gameType: widget.game_type || 'quiz',
        description: descriptionWith([widget.challenge && `Game challenge: ${widget.challenge}`,
          widget.player_controls?.length && `Player controls: ${JSON.stringify(widget.player_controls)}`,
          widget.physics_concept && `Physics concept: ${widget.physics_concept}`]),
        keyPoints, scoring: { correctPoints: 10, speedBonus: 5 }, languageDirective };
    default:
      return { title: outline.title, visualizationType: widget.visualization_type || 'custom',
        description: outline.description, keyPoints, objects: widget.objects || [],
        interactions: widget.interactions || [], languageDirective };
  }
}
function fixed(status, widgetType) {
  return { schema: RESULT, status, scope: 'CALLER_SUPPLIED_UNVERIFIED',
    operation: 'UPSTREAM_INTERACTIVE_PROMPT_ONLY', widget_type: widgetType, model_call: 'NOT_INVOKED',
    html_output: 'NOT_PRODUCED', full_generation: 'NOT_PERFORMED', core_authorization: 'NOT_ESTABLISHED',
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
  const promptId = TEMPLATES[request.outline.widget_type];
  const reads = [`templates/${promptId}/system.md`, ...SNIPPETS.map(s => `snippets/${s}.md`),
    `templates/${promptId}/user.md`];
  const index = installResolver();
  const { buildPrompt } = await import(pathToFileURL(index).href);
  if (typeof buildPrompt !== 'function') reject('UNEXPECTED_UPSTREAM_RESULT');
  const seen = [], oldRead = fs.readFileSync;
  let prompt;
  try {
    // Only the selected template and its three snippets are served from verified
    // buffers during the synchronous call; this is not an OS I/O sandbox.
    fs.readFileSync = function (name, encoding) {
      if (typeof name !== 'string' || encoding !== 'utf-8') reject('UNLISTED_TEMPLATE_READ');
      const rel = path.relative(DONOR, path.resolve(name)).split(path.sep).join('/');
      if (!reads.includes(rel)) reject('UNLISTED_TEMPLATE_READ');
      seen.push(rel); return files.get(rel).toString('utf8');
    };
    syncBuiltinESMExports();
    prompt = buildPrompt(promptId, variablesFor(request.outline, request.language_directive));
  } finally { fs.readFileSync = oldRead; syncBuiltinESMExports(); }
  if (JSON.stringify(seen) !== JSON.stringify(reads) || !exact(prompt, ['system', 'user']) ||
      typeof prompt.system !== 'string' || typeof prompt.user !== 'string' ||
      Buffer.byteLength(prompt.system, 'utf8') > 65536 || Buffer.byteLength(prompt.user, 'utf8') > 32768)
    reject('UNEXPECTED_UPSTREAM_RESULT');
  const out = fixed('BUILT', request.outline.widget_type);
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
  const out = fixed('REJECTED', null);
  out.error_code = error instanceof Rejection ? error.code : 'INTERNAL_FAILURE';
  process.stdout.write(JSON.stringify(out) + '\n');
}
