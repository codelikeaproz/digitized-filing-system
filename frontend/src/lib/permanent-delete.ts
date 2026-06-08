export function getPermanentDeleteConfirmationPhrase(displayName: string): string {
  return `DELETE ${displayName.trim()}`;
}
