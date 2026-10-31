import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {existsSync, lstatSync} from 'node:fs';
import {ensureLoaded, receiptPath} from '../../scripts/runtime/lm_studio_profile.mjs';

const profile = {model_key: 'qwen3.8-27b', identifier: 'aaos-deep-27b-mtp', ttl_seconds: 1800,
  load: {gpu: {ratio: 0.4}, contextLength: 2048, speculativeDraftMtp: true}};

test('does not load or evict when another LLM is already loaded', async () => {
  let loads = 0;
  const client = {llm: {listLoaded: async () => [{identifier: 'user-model', modelKey: 'other'}],
    load: async () => {loads++;}}};
  await assert.rejects(ensureLoaded(client, profile, {}), /SHARED_LLM_LOADED/);
  assert.equal(loads, 0);
});

test('existing identifier cannot silently redirect to another model or stale load settings', async () => {
  for (const existing of [
    {identifier: profile.identifier, modelKey: 'other'},
    {identifier: profile.identifier, modelKey: profile.model_key,
      getLoadConfig: async () => ({...profile.load, speculativeDraftMtp: false})},
  ]) {
    await assert.rejects(ensureLoaded({llm: {listLoaded: async () => [existing]}}, profile, {}),
      /IDENTIFIER_COLLISION|EXISTING_CONFIG_MISMATCH/);
  }
});

test('refuses a load whose effective configuration does not honor MTP', async () => {
  const client = {llm: {listLoaded: async () => [], load: async () => ({
    getLoadConfig: async () => ({...profile.load, speculativeDraftMtp: false}),
  })}};
  await assert.rejects(ensureLoaded(client, profile, {}), /EFFECTIVE_CONFIG_MISMATCH/);
});

test('reuses matching instance without reloading or changing its configuration', async () => {
  const existing = {identifier: profile.identifier, modelKey: profile.model_key,
    getLoadConfig: async () => profile.load};
  const receipt = {};
  assert.equal(await ensureLoaded({llm: {listLoaded: async () => [existing]}}, profile, receipt), existing);
  assert.equal(receipt.reused_existing, true);
});

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const ownedRun = process.env.ARCHEAXIS_RUN_ROOT;
const oldRoot = path.join(root, '.project-local/runs/lm-studio-profile');
const oldState = () => existsSync(oldRoot) ? [lstatSync(oldRoot).mtimeMs, lstatSync(oldRoot).size] : null;
const before = oldState();
function restoreOwnedRun() {
  if (ownedRun === undefined) delete process.env.ARCHEAXIS_RUN_ROOT;
  else process.env.ARCHEAXIS_RUN_ROOT = ownedRun;
}
function check(output, run) {
  assert.equal(path.basename(output), 'inspect.json');
  const rel = path.relative(path.join(root, '.project-local/runs'), output).split(path.sep);
  assert.equal(rel.length, 6);
  assert.match(rel[0], /^[0-9a-f]{10}$/);
  assert.equal(rel[2], 'artifacts');
  assert.equal(rel[3], 'lm-studio-profile');
  assert.match(rel[4], /^[0-9a-f]{32}$/);
  if (run) assert.equal(path.dirname(path.dirname(path.dirname(output))), path.join(run, 'artifacts'));
  assert.equal(existsSync(output), false);
  return output;
}
test('inherited canonical run uses independent UUID receipt directories', () => {
  const a=check(receiptPath('inspect', root), ownedRun);
  const b=check(receiptPath('inspect', root), ownedRun);
  assert.notEqual(a,b);
});
test('without inherited run dev allocates canonical run ownership', () => {
  delete process.env.ARCHEAXIS_RUN_ROOT;
  try { check(receiptPath('inspect', root)); }
  finally { restoreOwnedRun(); }
});
test('foreign run and invalid operation are refused without legacy writes', () => {
  process.env.ARCHEAXIS_RUN_ROOT=root;
  try { assert.throws(() => receiptPath('inspect', root)); }
  finally { restoreOwnedRun(); }
  assert.throws(() => receiptPath('../escape', root), /INVALID_ARGUMENT/);
  assert.deepEqual(oldState(), before);
});
