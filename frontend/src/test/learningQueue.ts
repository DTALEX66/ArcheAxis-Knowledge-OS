import {waitFor} from "@testing-library/react";

/** Select one original identity; labels may be absent or shared by many items. */
export function getLearningItemButton(itemKey: string, scope: ParentNode = document): HTMLButtonElement {
  const matches = Array.from(scope.querySelectorAll<HTMLButtonElement>("button[data-learning-item-key]"))
    .filter(button => button.getAttribute("data-learning-item-key") === itemKey);
  if (matches.length !== 1) throw new Error(`Expected one learning item ${itemKey}, got ${matches.length}`);
  return matches[0];
}
export function findLearningItemButton(itemKey: string, scope: ParentNode = document): Promise<HTMLButtonElement> {
  return waitFor(() => getLearningItemButton(itemKey, scope));
}
