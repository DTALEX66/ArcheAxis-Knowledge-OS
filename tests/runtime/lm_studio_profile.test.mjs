import test from 'node:test';
import assert from 'node:assert/strict';
import {ensureLoaded} from '../../scripts/runtime/lm_studio_profile.mjs';

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
