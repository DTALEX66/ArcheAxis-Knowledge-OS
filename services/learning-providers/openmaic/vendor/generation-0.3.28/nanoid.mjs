// Local replacement for the upstream nanoid dependency. It provides only the
// no-argument ID operation used by scene-builder.ts, using Node's CSPRNG.
import { randomBytes } from "node:crypto";

const alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz-";
export function nanoid() {
  return Array.from(randomBytes(21), value => alphabet[value & 63]).join("");
}
