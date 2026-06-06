/**
 * Client-side preview for auto-generated category codes.
 * Server assigns the final code (including dedupe) on create.
 */
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
