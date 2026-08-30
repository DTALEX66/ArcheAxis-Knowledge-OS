import type { SpaceId } from "./spaces";

// Adjacent spaces shown in the context subnav for each product space.
export const RELATED: Record<SpaceId, SpaceId[]> = {
  workspace: ["workspace", "library", "intake"],
  library: ["library", "intake", "vault"],
  intake: ["intake", "library", "exchange"],
  vault: ["vault", "evidence", "learning"],
  evidence: ["evidence", "vault", "ai-assets"],
  learning: ["learning", "vault", "ai-assets"],
  "ai-assets": ["ai-assets", "evidence", "learning"],
  exchange: ["exchange", "intake", "library"],
  settings: ["settings", "workspace", "library"],
};
