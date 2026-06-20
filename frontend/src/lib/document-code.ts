const DOCUMENT_CODE_PATTERN = /^[A-Za-z0-9-]+$/;

export function normalizeDocumentCode(value: string): string {
  return value.trim().toUpperCase();
}

export function validateDocumentCode(value: string): string | null {
  const code = normalizeDocumentCode(value);
  if (!code) {
    return "Document Code is required.";
  }
  if (!DOCUMENT_CODE_PATTERN.test(code)) {
    return "Document Code can contain letters, numbers, and hyphens only.";
  }
  return null;
}
