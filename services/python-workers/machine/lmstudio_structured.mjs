/** One prediction on an already loaded local instance. Only final content leaves this process. */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

async function predict() {
  const runtime = process.argv[2] === '--packaged-fast-local' ? {
    sdk: fileURLToPath(new URL('./lmstudio-sdk/node_modules/@lmstudio/sdk', import.meta.url)),
    sdk_version: '2.0.0',
    endpoint: 'ws://127.0.0.1:1234',
    model: 'aaos-fast-4b',
    model_key: 'qwen3.5-4b',
    reasoning_tokens: 1536,
  } : JSON.parse(readFileSync(new URL('./lmstudio-structured-runtime.json', import.meta.url), 'utf8'));
  const request = JSON.parse(readFileSync(0, 'utf8'));
  if (runtime.endpoint !== 'ws://127.0.0.1:1234' || runtime.model !== request.model
      || !path.isAbsolute(runtime.sdk) || !Number.isSafeInteger(runtime.reasoning_tokens)
      || runtime.reasoning_tokens < 1) throw Error('Invalid local structured worker configuration');
  const installed = JSON.parse(readFileSync(path.join(runtime.sdk, 'package.json'), 'utf8'));
  if (installed.name !== '@lmstudio/sdk' || installed.version !== runtime.sdk_version) throw Error('SDK mismatch');
  const {LMStudioClient} = await import(pathToFileURL(path.join(runtime.sdk, 'dist/index.mjs')).href);
  const quiet = () => {};
  const client = new LMStudioClient({baseUrl:runtime.endpoint, verboseErrorMessages:false,
                                     logger:{debug:quiet,info:quiet,warn:quiet,error:quiet}});
  const matches = (await client.llm.listLoaded()).filter(m => m.identifier === request.model && m.modelKey === runtime.model_key);
  if (matches.length !== 1) throw Error('Selected local instance is unavailable');
  const reasoningBudget = Math.min(runtime.reasoning_tokens, Math.floor(request.max_tokens * 3 / 4));
  const parent = process.ppid;
  const cancelled = new AbortController();
  const deadline = AbortSignal.timeout(request.timeout_ms);
  const monitor = setInterval(() => {
    try { process.kill(parent, 0); } catch (error) { if (error.code === 'ESRCH') cancelled.abort(); }
  }, 500);
  monitor.unref();
  try {
    const result = await matches[0].respond(request.prompt, {
      structured:{type:'json',jsonSchema:request.schema}, maxTokens:request.max_tokens, reasoningBudget,
      contextOverflowPolicy:'stopAtLimit',
      signal:AbortSignal.any([cancelled.signal, deadline])
    });
    const setting = result.predictionConfig.fields.find(f => f.key === 'llm.prediction.reasoning.budgetTokens')?.value;
    if (setting?.checked !== true || setting.value !== reasoningBudget) throw Error('Reasoning budget was not confirmed');
    const stop = result.stats.stopReason;
    const finish = ['eosFound','stopStringFound'].includes(stop) ? 'stop'
      : ['maxPredictedTokensReached','contextLengthReached'].includes(stop) ? 'length' : 'error';
    const usage = {};
    for (const [name, value] of Object.entries({input_tokens:result.stats.promptTokensCount,
             output_tokens:result.stats.predictedTokensCount,total_tokens:result.stats.totalTokensCount})) {
      if (Number.isSafeInteger(value) && value >= 0) usage[name] = value;
    }
    return {answer:result.nonReasoningContent, model:result.modelInfo.identifier, finish,
            reasoning_seen:Boolean(result.reasoningContent?.trim()), usage,
            transport:{protocol:'lmstudio-sdk', endpoint:runtime.endpoint, sdk_version:installed.version,
                       reasoning_tokens:setting.value, max_tokens:request.max_tokens, stop_reason:stop}};
  } catch (error) {
    if (deadline.aborted) throw new Error('PREDICTION_DEADLINE');
    throw error;
  } finally {
    clearInterval(monitor);
  }
}

try {
  process.stdout.write(JSON.stringify(await predict()));
} catch (error) {
  // Private material and provider exceptions must never appear in diagnostics.
  process.exitCode = error.message === 'PREDICTION_DEADLINE' ? 124 : 1;
}
