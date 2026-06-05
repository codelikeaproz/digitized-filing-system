/** Keep only digits — letters and special characters are not allowed. */
export function sanitizeEmployeeNumberInput(value: string): string {
  return value.replace(/\D/g, "");
}

/** Returns an error message when invalid, otherwise null. */
export function validateEmployeeNumber(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return "Employee number is required.";
  }
  if (!/^\d+$/.test(trimmed)) {
    return "Employee number must contain digits only.";
  }
  return null;
}
