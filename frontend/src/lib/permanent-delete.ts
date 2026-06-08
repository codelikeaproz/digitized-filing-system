export function getPermanentDeleteConfirmationPhrase(displayName: string): string {
  return `DELETE ${displayName.trim()}`;
}

export function getBulkPermanentDeleteConfirmationPhrase(count: number): string {
  const label = count === 1 ? "ITEM" : "ITEMS";
  return `DELETE ${count} ${label}`;
}
