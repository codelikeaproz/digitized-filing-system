import { formatPersonName } from "@/lib/utils";
import { validateOptionalEmployeeNumber } from "@/lib/employee-number";
import type { DocumentRequisitioner } from "@/types";

export const REQUISITIONER_SUFFIX_OPTIONS = [
  { value: "", label: "No Suffix" },
  { value: "Jr.", label: "Jr." },
  { value: "Sr.", label: "Sr." },
  { value: "I", label: "I" },
  { value: "II", label: "II" },
  { value: "III", label: "III" },
  { value: "IV", label: "IV" },
  { value: "V", label: "V" },
] as const;

const ALLOWED_SUFFIX_VALUES = new Set<string>(
  REQUISITIONER_SUFFIX_OPTIONS.map((option) => option.value)
);

export type RequisitionerInput = {
  employeeNumber: string;
  firstName: string;
  lastName: string;
  suffix: string;
};

export type RequisitionerRowErrors = {
  employeeNumber?: string;
  firstName?: string;
  lastName?: string;
  suffix?: string;
};

export type RequisitionerValidationResult = {
  isValid: boolean;
  rowErrors: RequisitionerRowErrors[];
  message?: string;
};

export function createEmptyRequisitioner(): RequisitionerInput {
  return { employeeNumber: "", firstName: "", lastName: "", suffix: "" };
}

export function splitFullName(fullName: string): Pick<RequisitionerInput, "firstName" | "lastName" | "suffix"> {
  const parts = formatPersonName(fullName).split(/\s+/).filter(Boolean);
  if (!parts.length) {
    return { firstName: "", lastName: "", suffix: "" };
  }

  let suffix = "";
  if (parts.length > 1 && ALLOWED_SUFFIX_VALUES.has(parts[parts.length - 1])) {
    suffix = parts[parts.length - 1];
    parts.pop();
  }

  if (!parts.length) {
    return { firstName: "", lastName: "", suffix };
  }
  if (parts.length === 1) {
    return { firstName: parts[0], lastName: "", suffix };
  }

  return {
    firstName: parts[0],
    lastName: parts.slice(1).join(" "),
    suffix,
  };
}

export function buildRequisitionerFullName(item: Pick<RequisitionerInput, "firstName" | "lastName" | "suffix">): string {
  const parts = [
    formatPersonName(item.firstName.trim()),
    formatPersonName(item.lastName.trim()),
    item.suffix.trim(),
  ].filter(Boolean);
  return parts.join(" ");
}

export function normalizeRequisitionerInput(item: RequisitionerInput): RequisitionerInput {
  return {
    employeeNumber: item.employeeNumber.trim(),
    firstName: formatPersonName(item.firstName.trim()),
    lastName: formatPersonName(item.lastName.trim()),
    suffix: item.suffix.trim(),
  };
}

export function toRequisitionerInput(item: DocumentRequisitioner): RequisitionerInput {
  if (item.firstName || item.lastName) {
    return {
      employeeNumber: item.employeeNumber || "",
      firstName: item.firstName || "",
      lastName: item.lastName || "",
      suffix: item.suffix || "",
    };
  }

  const split = splitFullName(item.fullName || "");
  return {
    employeeNumber: item.employeeNumber || "",
    firstName: split.firstName,
    lastName: split.lastName,
    suffix: split.suffix,
  };
}

export function formatRequisitionersDisplay(requisitioners: DocumentRequisitioner[]): string {
  return requisitioners
    .map((item) => buildRequisitionerFullName(toRequisitionerInput(item)))
    .filter(Boolean)
    .join(", ");
}

export function formatRequisitionersNamesList(requisitioners: DocumentRequisitioner[]): string {
  return requisitioners
    .map((item) => buildRequisitionerFullName(toRequisitionerInput(item)))
    .filter(Boolean)
    .join("\n");
}

export function getTitleTooltipRequisitioners(document: {
  requisitioners?: DocumentRequisitioner[];
  requestor?: string;
}): string {
  const namesList = formatRequisitionersNamesList(document.requisitioners || []);
  if (namesList) {
    return namesList;
  }

  const legacyName = document.requestor?.trim();
  if (!legacyName) {
    return "";
  }

  if (legacyName.includes(",")) {
    return legacyName
      .split(",")
      .map((part) => part.replace(/^\d+\s*-\s*/, "").trim())
      .filter(Boolean)
      .join("\n");
  }

  return legacyName.replace(/^\d+\s*-\s*/, "").trim();
}

export function getDocumentRequisitionersDisplay(document: {
  requisitioners?: DocumentRequisitioner[];
  requestor?: string;
}): string {
  if (document.requisitioners && document.requisitioners.length > 0) {
    const formatted = formatRequisitionersDisplay(document.requisitioners);
    if (formatted) {
      return formatted;
    }
  }
  return document.requestor?.trim() || "";
}

export function getRequisitionerTableCell(document: {
  requisitioners?: DocumentRequisitioner[];
  requestor?: string;
}): { label: string; tooltip?: string } {
  const requisitioners = document.requisitioners || [];
  const names = requisitioners
    .map((item) => buildRequisitionerFullName(toRequisitionerInput(item)))
    .filter(Boolean);

  if (names.length > 0) {
    if (names.length === 1) {
      return { label: names[0] };
    }
    return {
      label: `${names[0]} et al.`,
      tooltip: names.join("\n"),
    };
  }

  const legacyName = document.requestor?.trim();
  if (!legacyName) {
    return { label: "" };
  }

  if (legacyName.includes(",")) {
    const legacyNames = legacyName
      .split(",")
      .map((part) => part.replace(/^\d+\s*-\s*/, "").trim())
      .filter(Boolean);
    if (legacyNames.length > 1) {
      return { label: `${legacyNames[0]} et al.`, tooltip: legacyNames.join("\n") };
    }
    if (legacyNames.length === 1) {
      return { label: legacyNames[0] };
    }
  }

  const singleLegacy = legacyName.replace(/^\d+\s*-\s*/, "").trim();
  return { label: singleLegacy };
}

export function seedRequisitionersFromDocument(document: {
  requisitioners?: DocumentRequisitioner[];
  requestor?: string;
}): RequisitionerInput[] {
  if (document.requisitioners && document.requisitioners.length > 0) {
    return document.requisitioners.map((item) => toRequisitionerInput(item));
  }
  if (document.requestor?.trim()) {
    const split = splitFullName(document.requestor.replace(/^\d+\s*-\s*/, "").trim());
    return [{ employeeNumber: "", ...split }];
  }
  return [];
}

export function validateSingleRequisitioner(
  item: RequisitionerInput,
  existing: RequisitionerInput[],
  excludeIndex?: number
): { isValid: boolean; errors: RequisitionerRowErrors } {
  const errors: RequisitionerRowErrors = {};
  const employeeNumber = item.employeeNumber.trim();
  const firstName = formatPersonName(item.firstName.trim());
  const lastName = formatPersonName(item.lastName.trim());
  const suffix = item.suffix.trim();
  const employeeError = validateOptionalEmployeeNumber(employeeNumber);

  if (employeeError) {
    errors.employeeNumber = employeeError;
  } else if (
    employeeNumber &&
    existing.some(
      (row, index) => index !== excludeIndex && row.employeeNumber.trim() === employeeNumber
    )
  ) {
    errors.employeeNumber = "This employee number is already listed.";
  }

  if (!firstName) {
    errors.firstName = "First name is required.";
  }
  if (!lastName) {
    errors.lastName = "Last name is required.";
  }
  if (suffix && !ALLOWED_SUFFIX_VALUES.has(suffix)) {
    errors.suffix = "Select a valid suffix.";
  }

  return {
    isValid: !errors.employeeNumber && !errors.firstName && !errors.lastName && !errors.suffix,
    errors,
  };
}

export function validateRequisitioners(items: RequisitionerInput[]): RequisitionerValidationResult {
  const rowErrors: RequisitionerRowErrors[] = items.map(() => ({}));
  const seenEmployeeNumbers = new Set<string>();

  if (!items.length) {
    return {
      isValid: false,
      rowErrors,
      message: "At least one requisitioner is required.",
    };
  }

  let isValid = true;

  items.forEach((item, index) => {
    const validation = validateSingleRequisitioner(item, items, index);
    if (!validation.isValid) {
      rowErrors[index] = validation.errors;
      isValid = false;
      return;
    }

    const employeeNumber = item.employeeNumber.trim();
    if (employeeNumber) {
      if (seenEmployeeNumbers.has(employeeNumber)) {
        rowErrors[index].employeeNumber = "Duplicate employee numbers are not allowed.";
        isValid = false;
      } else {
        seenEmployeeNumbers.add(employeeNumber);
      }
    }
  });

  return { isValid, rowErrors };
}

export function serializeRequisitionersForApi(items: RequisitionerInput[]): DocumentRequisitioner[] {
  return items.map((item) => {
    const normalized = normalizeRequisitionerInput(item);
    return {
      employeeNumber: normalized.employeeNumber,
      firstName: normalized.firstName,
      lastName: normalized.lastName,
      suffix: normalized.suffix,
      fullName: buildRequisitionerFullName(normalized),
    };
  });
}
