/** Explicit local model loading; never edits provider settings or unloads shared instances. */
import {readFileSync, mkdirSync, writeFileSync, lstatSync, existsSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const configPath = path.join(root, 'config/model-profiles/lm-studio.json');

export function effectiveConfig(config) {
  return Object.fromEntries([
    'gpu', 'gpuStrictVramCap', 'offloadKVCacheToGpu', 'contextLength',
    'maxParallelPredictions', 'flashAttention', 'speculativeDraftMtp',
    'speculativeDraftSimple', 'speculativeDraftMaxTokens', 'speculativeDraftMinTokens',
  ].map(key => [key, config[key] ?? null]));
}

export function matchesProfile(actual, expected) {
  return Object.entries(expected).every(([key, value]) => key === 'gpu'
    ? actual.gpu?.ratio === value.ratio
    : actual[key] === value);
}

export async function ensureLoaded(client, profile, receipt) {
  const before = await client.llm.listLoaded();
  receipt.before = before.map(({identifier, modelKey}) => ({identifier, modelKey}));
  const existing = before.find(model => model.identifier === profile.identifier);
  if (existing) {
    if (existing.modelKey !== profile.model_key) throw Error('IDENTIFIER_COLLISION');
    receipt.effective_config = effectiveConfig(await existing.getLoadConfig());
    if (!matchesProfile(receipt.effective_config, profile.load)) throw Error('EXISTING_CONFIG_MISMATCH');
    receipt.reused_existing = true;
    return existing;
  }
  // On this profile's 8GB target, do not evict another application's loaded LLM.
  if (before.length) throw Error('SHARED_LLM_LOADED');
  receipt.load_requested = true;
  const started = performance.now();
  const model = await client.llm.load(profile.model_key, {
    identifier: profile.identifier, deviceIdentifier: null, ttl: profile.ttl_seconds,
    signal: AbortSignal.timeout(180000), config: profile.load,
  });
  receipt.created_instance = true;
  receipt.load_elapsed_s = (performance.now() - started) / 1000;
  receipt.effective_config = effectiveConfig(await model.getLoadConfig());
  if (!matchesProfile(receipt.effective_config, profile.load)) throw Error('EFFECTIVE_CONFIG_MISMATCH');
  return model;
}

function projectLocalPath(relative) {
  const resolved = path.resolve(root, relative);
  const local = path.join(root, '.project-local');
  if (!resolved.startsWith(local + path.sep)) throw Error('OUTSIDE_PROJECT_LOCAL');
  for (let current = resolved; current !== root; current = path.dirname(current)) {
    if (existsSync(current) && lstatSync(current).isSymbolicLink()) throw Error('LINKED_LOCAL_PATH');
  }
  return resolved;
}

async function main(args) {
  const operation = args.shift() ?? 'inspect';
  if (!['inspect', 'load', 'smoke'].includes(operation) || args.length > 1) throw Error('INVALID_ARGUMENT');
  const declaration = JSON.parse(readFileSync(configPath, 'utf8'));
  const profileName = args[0] ?? 'deep-mtp';
  const profile = declaration.profiles[profileName];
  if (!profile) throw Error('UNKNOWN_PROFILE');
  const sdkRoot = projectLocalPath('.project-local/tools/lm-studio-sdk/node_modules/@lmstudio/sdk');
  const packageInfo = JSON.parse(readFileSync(path.join(sdkRoot, 'package.json'), 'utf8'));
  if (packageInfo.version !== declaration.sdk.version) throw Error('SDK_VERSION_MISMATCH');
  const {LMStudioClient} = await import(pathToFileURL(path.join(sdkRoot, 'dist/index.mjs')).href);
  const quiet = () => {};
  const client = new LMStudioClient({baseUrl: declaration.endpoint, verboseErrorMessages: false,
    logger: {info: quiet, warn: quiet, error: quiet, debug: quiet}});
  const output = projectLocalPath(`.project-local/runs/lm-studio-profile/${Date.now()}-${operation}.json`);
  const receipt = {schema: 'archeaxis.lm-studio-profile-result/v1', observed_at: new Date().toISOString(),
    operation, profile: profileName, model_key: profile.model_key, identifier: profile.identifier,
    evidence_level: 'REAL_LOCAL_SDK_NOT_APPLICATION_QUALIFICATION', status: 'RUNNING'};
  let model;
  try {
    if (operation === 'inspect') {
      receipt.loaded = await Promise.all((await client.llm.listLoaded()).map(async loaded => ({
        identifier: loaded.identifier, model_key: loaded.modelKey,
        effective_config: effectiveConfig(await loaded.getLoadConfig()),
      })));
      receipt.status = 'READ_VERIFIED';
    } else {
      model = await ensureLoaded(client, profile, receipt);
      if (operation === 'smoke') {
        const start = performance.now();
        const result = await model.respond('Synthetic test: return exactly AAOS-MTP-READY, without explanation.', {
          temperature: 0, seed: 42, maxTokens: 1024, contextOverflowPolicy: 'stopAtLimit',
          signal: AbortSignal.timeout(120000),
        });
        receipt.smoke = {elapsed_s: (performance.now() - start) / 1000,
          literal_present: result.nonReasoningContent.includes('AAOS-MTP-READY'),
          observed_model_key: result.modelInfo.modelKey, observed_identifier: result.modelInfo.identifier,
          stats: Object.fromEntries(['stopReason', 'tokensPerSecond', 'timeToFirstTokenSec',
            'promptTokensCount', 'predictedTokensCount', 'totalDraftTokensCount',
            'acceptedDraftTokensCount', 'rejectedDraftTokensCount'].map(key => [key, result.stats[key] ?? null]))};
        if (!receipt.smoke.literal_present || result.stats.stopReason !== 'eosFound'
            || result.modelInfo.modelKey !== profile.model_key || result.modelInfo.identifier !== profile.identifier)
          throw Error('SMOKE_UNVERIFIED');
      }
      receipt.status = 'PASS_LOAD_READBACK';
      if (operation === 'smoke') receipt.status = 'PASS_SYNTHETIC_SDK_SMOKE';
      receipt.instance_kept_available_with_ttl_seconds = profile.ttl_seconds;
    }
  } catch (error) {
    receipt.status = 'PARTIAL';
    receipt.reason_code = /^[A-Z_]+$/.test(error?.message ?? '') ? error.message : 'LOCAL_RUNTIME_FAILURE';
    receipt.error_type = error?.constructor?.name ?? 'Unknown';
    if (receipt.created_instance) {
      try {
        const owned = (await client.llm.listLoaded()).filter(value =>
          value.identifier === profile.identifier && value.modelKey === profile.model_key);
        if (owned.length === 1) await owned[0].unload();
        receipt.failed_owned_instance_unloaded = !(await client.llm.listLoaded()).some(value => value.identifier === profile.identifier);
      } catch {receipt.failed_owned_instance_unloaded = 'UNVERIFIED';}
    }
    process.exitCode = 1;
  } finally {
    mkdirSync(path.dirname(output), {recursive: true});
    writeFileSync(output, JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
    console.log(JSON.stringify({status: receipt.status, reason_code: receipt.reason_code, receipt: output}));
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch(error => {
    console.error(JSON.stringify({status: 'BLOCKED', reason_code:
      /^[A-Z_]+$/.test(error?.message ?? '') ? error.message : 'SETUP_UNAVAILABLE'}));
    process.exitCode = 1;
  });
}
