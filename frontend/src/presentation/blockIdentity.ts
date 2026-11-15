import type { JSONContent } from "@tiptap/core";

type Identity = { block_id?: string; canvas_node_id?: string; text: string };

function nodeText(node: JSONContent): string {
  if (typeof node.text === "string") return node.text;
  return (node.content ?? []).map(nodeText).join("");
}

function identities(nodes: JSONContent[] | undefined): Identity[] {
  return (nodes ?? []).map(node => {
    const attrs = (node.attrs ?? {}) as Record<string, unknown>;
    return {
      block_id: typeof attrs.block_id === "string" && attrs.block_id ? attrs.block_id : undefined,
      canvas_node_id: typeof attrs.canvas_node_id === "string" && attrs.canvas_node_id ? attrs.canvas_node_id : undefined,
      text: nodeText(node),
    };
  });
}

/** A body edit must not break the identity of the block it rewrites.
 *
 * Block and canvas node IDs are what references, revision checks and canvas
 * mapping are keyed by. The editor may hand back a rewritten body without those
 * IDs, or with a freshly minted ID for a block the person only changed the text
 * of, so the previous version's identities are carried back onto the rewritten
 * blocks: an identity the block still owns is kept, otherwise matching text is
 * used first and the same position second. An identity is never used twice, and
 * a block that matches nothing keeps its own ID instead of borrowing a wrong
 * one. */
export function preserveBlockIdentities(previous: JSONContent | undefined, next: JSONContent): JSONContent {
  const old = identities(Array.isArray(previous?.content) ? previous.content : undefined);
  const nodes = Array.isArray(next?.content) ? next.content : [];
  if (!old.length || !nodes.length) return next;
  const known = new Set(old.map(row => row.block_id).filter((id): id is string => typeof id === "string"));
  const carried = nodes.filter(node => {
    const id = ((node.attrs ?? {}) as Record<string, unknown>).block_id;
    return typeof id === "string" && known.has(id);
  }).length;
  // A body that kept none of its identities was rewritten wholesale: no part of
  // the old document survived, so the editor cannot map the old blocks onto the
  // new ones and the previous identities have to be carried back here.
  const wholesale = known.size > 0 && carried === 0;
  const used = new Set<string>();
  const content = nodes.map((node, index) => {
    const attrs = { ...((node.attrs ?? {}) as Record<string, unknown>) };
    const current = typeof attrs.block_id === "string" && attrs.block_id ? attrs.block_id : undefined;
    if (current) {
      used.add(current);
      if (known.has(current)) {
        const owner = old.find(row => row.block_id === current);
        if (owner?.canvas_node_id && !attrs.canvas_node_id) attrs.canvas_node_id = owner.canvas_node_id;
        return { ...node, attrs };
      }
    }
    if (!wholesale) return { ...node, attrs };
    const text = nodeText(node);
    const sameText = old.find(row => row.block_id && !used.has(row.block_id) && row.text && row.text === text);
    const sameOrder = old[index];
    const source = sameText ?? (sameOrder && sameOrder.block_id && !used.has(sameOrder.block_id) ? sameOrder : undefined);
    if (!source || !source.block_id) return { ...node, attrs };
    used.add(source.block_id);
    const merged: Record<string, unknown> = { ...attrs, block_id: source.block_id };
    if (source.canvas_node_id && !attrs.canvas_node_id) merged.canvas_node_id = source.canvas_node_id;
    return { ...node, attrs: merged };
  });
  return { ...next, content };
}
