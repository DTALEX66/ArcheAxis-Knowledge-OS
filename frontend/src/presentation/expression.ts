/** Controlled Document projection. Types are generated from the canonical JSON schema. */
import type { ExpressionDocument, ExpressionMedia } from "../api/generated/expression-contract";
export type { ExpressionDocument, ExpressionMedia, ExpressionNode, ExpressionEdge, ExpressionContext } from "../api/generated/expression-contract";
export const EXPRESSION_LIMITS = { nodes: 500, edges: 1000, coordinate: 100000, dimension: 10000, textBytes: 16384, labelBytes: 1024 } as const;
export const EXPRESSION_MEDIA_TYPES = new Set(["image/png", "image/jpeg", "image/gif", "image/webp", "audio/wav", "audio/mpeg", "video/mp4", "video/webm"]);
export function validExpressionMedia(media: ExpressionMedia): boolean {
  return /^[A-Za-z0-9_.-]{1,256}$/.test(media.source_id) && media.source_id !== "." && media.source_id !== ".." && /^[a-f0-9]{64}$/.test(media.sha256) && EXPRESSION_MEDIA_TYPES.has(media.media_type);
}
export function expressionTextBytes(text: string): number { return new TextEncoder().encode(text).length; }
/**
 * Read validator enforces the canonical expression.schema.json shape and runtime budgets.
 * Strict read validation returns the original payload intact, never strips unknown fields.
 */
function expressionObject(value: unknown): value is Record<string, unknown> { return value !== null && typeof value === "object" && !Array.isArray(value); }
function expressionKeys(value: Record<string, unknown>, keys: string[]): boolean { return Object.keys(value).every(key => keys.includes(key)); }
function expressionId(value: unknown, max: number): value is string { return typeof value === "string" && /^[A-Za-z0-9_.-]+$/.test(value) && value.length <= max && value !== "." && value !== ".."; }
function inertMetadata(value: unknown, depth: number): boolean {
  if (depth > 4) return false;
  if (value === null || typeof value === "boolean") return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value === "string") return expressionTextBytes(value) <= 4096;
  if (Array.isArray(value)) return value.length <= 32 && value.every(item => inertMetadata(item, depth + 1));
  if (expressionObject(value)) return Object.keys(value).length <= 32 && Object.keys(value).every(key => expressionId(key, 128)) && Object.values(value).every(item => inertMetadata(item, depth + 1));
  return false;
}
export function parseExpressionDocument(value: unknown): ExpressionDocument | null {
  if (!expressionObject(value) || !expressionKeys(value, ["schema", "nodes", "edges", "context", "capability_metadata"]) || value.schema !== "archeaxis.expression/v1" || !Array.isArray(value.nodes) || !Array.isArray(value.edges) || value.nodes.length > EXPRESSION_LIMITS.nodes || value.edges.length > EXPRESSION_LIMITS.edges) return null;
  const ids = new Set<string>();
  for (const node of value.nodes) {
    if (!expressionObject(node) || !expressionKeys(node, ["id", "type", "x", "y", "width", "height", "text", "media"]) || !expressionId(node.id, 128) || ids.has(node.id) || (node.type !== "text" && node.type !== "media") || typeof node.text !== "string" || expressionTextBytes(node.text) > EXPRESSION_LIMITS.textBytes) return null;
    if (![node.x, node.y].every(v => typeof v === "number" && Number.isFinite(v) && Math.abs(v) <= EXPRESSION_LIMITS.coordinate) || ![node.width, node.height].every(v => typeof v === "number" && Number.isFinite(v) && v >= 1 && v <= EXPRESSION_LIMITS.dimension)) return null;
    if (node.type === "text" && node.media != null) return null;
    if (node.type === "media") {
      const media = node.media;
      if (!expressionObject(media) || !expressionKeys(media, ["source_id", "sha256", "media_type"]) || !expressionId(media.source_id, 256) || typeof media.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(media.sha256) || typeof media.media_type !== "string" || !EXPRESSION_MEDIA_TYPES.has(media.media_type)) return null;
    }
    ids.add(node.id);
  }
  const edgeIds = new Set<string>();
  for (const edge of value.edges) {
    if (!expressionObject(edge) || !expressionKeys(edge, ["id", "fromNode", "toNode", "label"]) || !expressionId(edge.id, 128) || edgeIds.has(edge.id) || typeof edge.fromNode !== "string" || typeof edge.toNode !== "string" || !ids.has(edge.fromNode) || !ids.has(edge.toNode) || typeof edge.label !== "string" || expressionTextBytes(edge.label) > EXPRESSION_LIMITS.labelBytes) return null;
    edgeIds.add(edge.id);
  }
  if (value.context != null) {
    if (!expressionObject(value.context) || !expressionKeys(value.context, ["knowledge_id", "course_id", "teaching_record_id"]) || !Object.values(value.context).every(v => v == null || expressionId(v, 256))) return null;
  }
  if (value.capability_metadata != null) {
    if (!expressionObject(value.capability_metadata) || !inertMetadata(value.capability_metadata, 0)) return null;
    try { if (expressionTextBytes(JSON.stringify(value.capability_metadata)) > 16384) return null; } catch { return null; }
  }
  return value as unknown as ExpressionDocument;
}
