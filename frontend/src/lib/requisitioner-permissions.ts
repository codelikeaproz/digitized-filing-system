export function canManageRequisitioners(role?: string | null) {
  return role?.toLowerCase() === "admin";
}

/** Upload/edit document metadata: all uploaders may edit manual requisitioner fields. */
export function canEditManualRequisitionerOnDocument(role?: string | null) {
  const normalized = role?.toLowerCase();
  return normalized === "admin" || normalized === "dept_head" || normalized === "staff";
}

export function isManualRequisitionerEmployeeNumberLocked(role?: string | null, isEdit = false) {
  return isEdit && !canEditManualRequisitionerOnDocument(role);
}

export const EMPLOYEE_NUMBER_TAGGED_LOCK_HELPER =
  "Employee Number cannot be modified because this requisitioner is referenced by existing documents.";

export function canOverrideEmployeeNumberLock(role?: string | null) {
  return role?.toLowerCase() === "admin";
}

export function isEmployeeNumberLockedByTags(
  taggedCount: number,
  canChangeFromApi?: boolean
) {
  if (typeof canChangeFromApi === "boolean") {
    return !canChangeFromApi;
  }
  return taggedCount > 0;
}
