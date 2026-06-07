/** Short label used when displaying employee numbers in lists and tables. */
export const EMPLOYEE_NUMBER_DISPLAY_LABEL = "Emp. No.";

/** Shown when a document requisitioner has no employee number. */
export const NO_EMPLOYEE_NUMBER_DISPLAY = "No Emp No. Provided";

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

/** Requisitioner list display — includes fallback when employee number is omitted. */
export function formatRequisitionerEmployeeNumberDisplay(value?: string | null): string {
  return formatEmployeeNumberDisplay(value) ?? NO_EMPLOYEE_NUMBER_DISPLAY;
}

/** Returns an error message when invalid, otherwise null. Empty values are allowed. */
export function validateOptionalEmployeeNumber(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (!/^\d+$/.test(trimmed)) {
    return "Employee number must contain digits only.";
  }
  return null;
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
