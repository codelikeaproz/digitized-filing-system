export function canAccessRequisitionersDirectory(role?: string | null) {
  const normalized = role?.toLowerCase();
  return normalized === "admin" || normalized === "dept_head";
}

export function canManageRequisitioners(role?: string | null) {
  return role?.toLowerCase() === "admin";
}

export function canSearchRequisitioners(_role?: string | null) {
  return true;
}

export function canChangeEmployeeNumber(role?: string | null) {
  const normalized = role?.toLowerCase();
  return normalized === "admin" || normalized === "dept_head";
}

export function isEmployeeNumberLocked(role?: string | null, isEdit = false) {
  return isEdit && !canChangeEmployeeNumber(role);
}

export const EMPLOYEE_NUMBER_LOCKED_HELPER =
  "Only Admin or Dept Head can change the employee number after save.";

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
