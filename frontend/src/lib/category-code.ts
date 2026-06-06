/**
 * Client-side preview for auto-generated category codes.
 * Server assigns the final code (including dedupe) on create and rename.
 */
export const GENERATED_DOCUMENT_CODE_PATTERN = /^([A-Z0-9]+)-(\d{4})-(\d{6})$/;

export function previewCategoryCode(name: string, existingCodes: string[] = []): string {
  const letters = (name || "").replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  const base = letters ? letters.slice(0, 3) : "CAT";
  const used = new Set(existingCodes.map((code) => code.toUpperCase()));
  if (!used.has(base)) {
    return base;
  }
  for (let suffix = 2; suffix < 100; suffix += 1) {
    const candidate = `${base}${suffix}`.slice(0, 10);
    if (!used.has(candidate)) {
      return candidate;
    }
  }
  return base;
}

/** Preview prefix swap for auto-generated document codes (display only). */
export function swapDocumentCodePrefixPreview(
  currentCode: string,
  newCategoryCode: string
): string | null {
  const normalized = (currentCode || "").trim().toUpperCase();
  const match = normalized.match(GENERATED_DOCUMENT_CODE_PATTERN);
  if (!match) return null;

  const prefix = (newCategoryCode || "").trim().toUpperCase();
  if (!prefix || prefix === match[1]) return normalized;
  return `${prefix}-${match[2]}-${match[3]}`;
}
