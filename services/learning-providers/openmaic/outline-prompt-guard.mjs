/** A single, bounded text callback; no model, process or network operations. */
const MAX_PROMPT_BYTES = 200_000;

export function createPromptGuard(expected, deliver) {
  const state = { calls: 0, failure: null, system: null, user: null };
  const fail = code => {
    state.failure = code;
    throw new Error(code);
  };
  async function callback(system, user, images) {
    state.calls++;
    if (state.calls !== 1) return fail("MULTIPLE_CALLBACKS");
    if (typeof system !== "string" || typeof user !== "string" ||
        !system.isWellFormed() || !user.isWellFormed() ||
        Buffer.byteLength(system, "utf8") > MAX_PROMPT_BYTES ||
        Buffer.byteLength(user, "utf8") > MAX_PROMPT_BYTES)
      return fail("PROMPT_INVALID_OR_OVERSIZED");
    if (images !== undefined && (!Array.isArray(images) || images.length !== 0))
      return fail("IMAGES_UNSUPPORTED");
    state.system = system;
    state.user = user;
    if (expected && (system !== expected.system || user !== expected.user))
      return fail("PROMPT_MISMATCH");
    return deliver(system, user);
  }
  return { callback, state };
}
