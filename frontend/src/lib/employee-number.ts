/** Short label used when displaying employee numbers in lists and tables. */
export const EMPLOYEE_NUMBER_DISPLAY_LABEL = "Emp. No.";

/** Keep only digits — letters and special characters are not allowed. */
export function sanitizeEmployeeNumberInput(value: string): string {
  return value.replace(/\D/g, "");
}

/** Returns formatted display text, e.g. "Emp. No. 1451511", or null when empty. */
export function formatEmployeeNumberDisplay(value?: string | null): string | null {
  const trimmed = (value ?? "").trim();
  if (!trimmed) {
    return null;
  }
  return `${EMPLOYEE_NUMBER_DISPLAY_LABEL} ${trimmed}`;
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
