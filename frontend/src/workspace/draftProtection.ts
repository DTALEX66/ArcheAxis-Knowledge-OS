import { useId } from "react";

/** A view keeps its own owner even without a document lease or Dock provider. */
export function useDraftOwner(scope: string): string {
  return `${scope}:${useId()}`;
}

/** Saving or closing one view can release only that view's content guard. */
export function updateDraftOwners(owners: Set<string>, detail: unknown): boolean {
  let owner: string;
  let dirty: boolean;
  if (typeof detail === "boolean") {
    // Compatibility for older callers; current content views publish an owner.
    owner = "legacy";
    dirty = detail;
  } else if (detail && typeof detail === "object" && "owner" in detail && "dirty" in detail &&
      typeof detail.owner === "string" && detail.owner.length > 0 && typeof detail.dirty === "boolean") {
    owner = detail.owner;
    dirty = detail.dirty;
  } else {
    return owners.size > 0;
  }
  if (dirty) owners.add(owner); else owners.delete(owner);
  return owners.size > 0;
}
