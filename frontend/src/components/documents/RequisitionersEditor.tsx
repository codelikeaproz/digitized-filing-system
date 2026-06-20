import { useEffect, useMemo, useState } from "react";
import { Loader2, Pencil, Plus, Search, Trash2, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn, formatPersonName } from "@/lib/utils";
import { api, type PaginatedResponse } from "@/lib/api";
import { toast } from "sonner";
import {
  formatEmployeeNumberInput,
  formatRequisitionerEmployeeNumberDisplay,
  EMPLOYEE_NUMBER_PLACEHOLDER,
  EMPLOYEE_NUMBER_HELPER_TEXT,
  sanitizeEmployeeNumberInput,
} from "@/lib/employee-number";
import type { EmployeeDirectoryEntry } from "@/types";
import {
  buildRequisitionerFullName,
  createEmptyRequisitioner,
  isDirectoryLinkedRequisitioner,
  isRequisitionerAlreadyOnDocument,
  normalizeRequisitionerInput,
  REQUISITIONER_SUFFIX_OPTIONS,
  type RequisitionerInput,
  type RequisitionerRowErrors,
  validateSingleRequisitioner,
} from "@/lib/requisitioner";
import { useAuth } from "@/lib/auth-context";
import {
  canEditManualRequisitionerOnDocument,
  isManualRequisitionerEmployeeNumberLocked,
} from "@/lib/requisitioner-permissions";

type RequisitionersEditorProps = {
  value: RequisitionerInput[];
  onChange: (value: RequisitionerInput[]) => void;
  rowErrors?: RequisitionerRowErrors[];
  listError?: string;
  disabled?: boolean;
  className?: string;
};

export function RequisitionersEditor({
  value,
  onChange,
  rowErrors = [],
  listError,
  disabled = false,
  className,
}: RequisitionersEditorProps) {
  const { user } = useAuth();
  const canEditManualRequisitioner = canEditManualRequisitionerOnDocument(user?.role);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [draft, setDraft] = useState<RequisitionerInput>(createEmptyRequisitioner());
  const [draftReadOnly, setDraftReadOnly] = useState(false);
  const [draftErrors, setDraftErrors] = useState<RequisitionerRowErrors>({});
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [employeeResults, setEmployeeResults] = useState<EmployeeDirectoryEntry[]>([]);
  const [employeeSearchLoading, setEmployeeSearchLoading] = useState(false);
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState<Set<string>>(new Set());
  const [isSavingRequisitioner, setIsSavingRequisitioner] = useState(false);

  const documentEmployeeNumbers = useMemo(
    () =>
      new Set(
        value
          .map((row) => sanitizeEmployeeNumberInput(row.employeeNumber))
          .filter(Boolean)
      ),
    [value]
  );

  const selectableEmployeeResults = useMemo(
    () =>
      employeeResults.filter(
        (employee) => !isRequisitionerAlreadyOnDocument(value, employee.employeeNumber, employee.id)
      ),
    [employeeResults, value]
  );

  const suffixOptions = useMemo(() => {
    const options = REQUISITIONER_SUFFIX_OPTIONS.map((option) => ({ ...option }));
    if (draft.suffix && !options.some((option) => option.value === draft.suffix)) {
      options.push({ value: draft.suffix, label: draft.suffix });
    }
    return options;
  }, [draft.suffix]);

  useEffect(() => {
    const query = employeeSearch.trim();
    if (!query) {
      setEmployeeResults([]);
      return;
    }

    let cancelled = false;
    setEmployeeSearchLoading(true);
    const timer = setTimeout(async () => {
      try {
        const data = await api.get<PaginatedResponse<EmployeeDirectoryEntry>>("/api/employees", {
          search: query,
          page_size: 50,
        });
        if (!cancelled) {
          setEmployeeResults(data.results);
        }
      } catch {
        if (!cancelled) {
          setEmployeeResults([]);
        }
      } finally {
        if (!cancelled) {
          setEmployeeSearchLoading(false);
        }
      }
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [employeeSearch]);

  const toggleEmployeeSelection = (employeeId: string, checked: boolean) => {
    setSelectedEmployeeIds((current) => {
      const next = new Set(current);
      if (checked) {
        next.add(employeeId);
      } else {
        next.delete(employeeId);
      }
      return next;
    });
  };

  const addSelectedEmployees = () => {
    const selected = employeeResults.filter((employee) => selectedEmployeeIds.has(employee.id));
    if (selected.length === 0) return;

    const existingNumbers = new Set(documentEmployeeNumbers);
    const additions: RequisitionerInput[] = [];
    let skippedCount = 0;

    for (const employee of selected) {
      const employeeNumber = sanitizeEmployeeNumberInput(employee.employeeNumber);
      if (employeeNumber && existingNumbers.has(employeeNumber)) {
        skippedCount += 1;
        continue;
      }
      additions.push(
        normalizeRequisitionerInput({
          employeeId: employee.id,
          source: "directory",
          employeeNumber,
          firstName: employee.firstName,
          lastName: employee.lastName,
          suffix: employee.suffix || "",
        })
      );
      if (employeeNumber) {
        existingNumbers.add(employeeNumber);
      }
    }

    if (additions.length === 0) {
      if (skippedCount > 0) {
        toast.info("Selected requisitioners are already in this document.");
      }
      return;
    }

    if (skippedCount > 0) {
      toast.info(`${skippedCount} selected requisitioner(s) were already in this document and were skipped.`);
    }

    onChange([...value, ...additions]);
    setSelectedEmployeeIds(new Set());
    setEmployeeSearch("");
    setEmployeeResults([]);
  };

  const resetDraft = () => {
    setDraft(createEmptyRequisitioner());
    setDraftErrors({});
    setDraftReadOnly(false);
    setEditingIndex(null);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    resetDraft();
  };

  const openAddModal = () => {
    resetDraft();
    setIsModalOpen(true);
  };

  const openEditModal = (index: number) => {
    const row = value[index];
    setEditingIndex(index);
    setDraft({ ...row });
    setDraftErrors({});
    setDraftReadOnly(isDirectoryLinkedRequisitioner(row));
    setIsModalOpen(true);
  };

  const removeRow = (index: number) => {
    onChange(value.filter((_, rowIndex) => rowIndex !== index));
  };

  const handleSaveRequisitioner = async () => {
    if (draftReadOnly) {
      closeModal();
      return;
    }

    const validation = validateSingleRequisitioner(draft, value, editingIndex ?? undefined);
    setDraftErrors(validation.errors);
    if (!validation.isValid) {
      return;
    }

    const normalized = normalizeRequisitionerInput({
      ...draft,
      source: draft.source || "manual",
    });
    if (editingIndex !== null && !canEditManualRequisitioner) {
      normalized.employeeNumber = value[editingIndex]?.employeeNumber || "";
    }

    if (!isDirectoryLinkedRequisitioner(normalized)) {
      setIsSavingRequisitioner(true);
      try {
        const duplicateCheck = await api.post<{
          blocked: boolean;
          message?: string;
          matches?: Array<{ id: string; fullName: string; employeeNumber?: string }>;
        }>("/api/employees/check-duplicate", {
          employeeNumber: normalized.employeeNumber,
          firstName: normalized.firstName,
          lastName: normalized.lastName,
          suffix: normalized.suffix,
          excludeEmployeeId: normalized.employeeId,
        });
        if (duplicateCheck.blocked) {
          setDraftErrors({
            employeeNumber: duplicateCheck.message,
          });
          toast.error(duplicateCheck.message || "This requisitioner already exists in the directory.");
          return;
        }
      } catch (error: any) {
        toast.error(error.message || "Failed to validate requisitioner.");
        return;
      } finally {
        setIsSavingRequisitioner(false);
      }
    }

    if (editingIndex === null) {
      onChange([...value, normalized]);
    } else {
      onChange(value.map((row, index) => (index === editingIndex ? normalized : row)));
    }
    closeModal();
  };

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between gap-2">
        <Label className="text-xs font-semibold uppercase text-muted-foreground">
          Requisitioners <span className="text-destructive">*</span>
        </Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={openAddModal}
          disabled={disabled}
          className="h-8 gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Manually
        </Button>
      </div>

      <div className="rounded-lg border bg-muted/20 p-3 space-y-3">
        <Label className="text-xs font-semibold uppercase text-muted-foreground">
          Search Requisitioners Directory
        </Label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={employeeSearch}
            onChange={(event) => setEmployeeSearch(event.target.value)}
            placeholder="Search requisitioners by number or name..."
            className="pl-9"
            disabled={disabled}
          />
        </div>
        {employeeSearchLoading && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Searching...
          </div>
        )}
        {!employeeSearchLoading && employeeSearch.trim() && employeeResults.length === 0 && (
          <p className="text-xs text-muted-foreground">No requisitioners found in the directory.</p>
        )}
        {!employeeSearchLoading &&
          employeeSearch.trim() &&
          employeeResults.length > 0 &&
          selectableEmployeeResults.length === 0 && (
            <p className="text-xs text-muted-foreground">
              All matching requisitioners are already in this document.
            </p>
          )}
        {employeeResults.length > 0 && (
          <div className="max-h-40 space-y-2 overflow-y-auto">
            {employeeResults.map((employee) => {
              const alreadyOnDocument = isRequisitionerAlreadyOnDocument(
                value,
                employee.employeeNumber,
                employee.id
              );
              return (
              <label
                key={employee.id}
                className={cn(
                  "flex items-start gap-2 rounded-md border bg-background p-2 text-sm",
                  alreadyOnDocument ? "cursor-not-allowed opacity-70" : "cursor-pointer"
                )}
              >
                <Checkbox
                  checked={selectedEmployeeIds.has(employee.id)}
                  onCheckedChange={(checked) => toggleEmployeeSelection(employee.id, checked === true)}
                  disabled={disabled || alreadyOnDocument}
                />
                <span className="min-w-0 flex-1">
                  <span className="text-xs text-muted-foreground">
                    {formatRequisitionerEmployeeNumberDisplay(employee.employeeNumber)}
                  </span>
                  <span className="mx-2 text-muted-foreground">—</span>
                  <span className="font-medium">{employee.fullName}</span>
                  {alreadyOnDocument && (
                    <span className="mt-1 block text-[11px] font-medium text-amber-700">
                      Already in this document
                    </span>
                  )}
                </span>
              </label>
            );
            })}
          </div>
        )}
        {selectedEmployeeIds.size > 0 && (
          <Button
            type="button"
            size="sm"
            onClick={addSelectedEmployees}
            disabled={disabled || selectableEmployeeResults.every((employee) => !selectedEmployeeIds.has(employee.id))}
            className="bg-[#0A4D27] hover:bg-[#083E1D] text-white"
          >
            Add Selected ({selectedEmployeeIds.size})
          </Button>
        )}
      </div>

      <div className="space-y-2 min-h-[24px]">
        {value.length > 0 ? (
          value.map((row, index) => {
            const errors = rowErrors[index] || {};
            const displayName = buildRequisitionerFullName(row) || "—";
            const displayEmployeeNumber = formatRequisitionerEmployeeNumberDisplay(row.employeeNumber);

            return (
              <div
                key={`requisitioner-${index}-${row.employeeNumber}-${displayName}`}
                className={cn(
                  "flex items-center justify-between gap-3 rounded-lg border bg-card/50 p-3",
                  (errors.employeeNumber || errors.firstName || errors.lastName || errors.suffix) &&
                    "border-destructive/60"
                )}
              >
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                    <UserRound className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{displayName}</p>
                    <p className="font-mono text-xs text-muted-foreground">{displayEmployeeNumber}</p>
                    {(errors.employeeNumber || errors.firstName || errors.lastName || errors.suffix) && (
                      <p className="mt-1 text-[11px] font-medium text-destructive">
                        {errors.employeeNumber || errors.firstName || errors.lastName || errors.suffix}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-1">
                  {!isDirectoryLinkedRequisitioner(row) && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => openEditModal(index)}
                      disabled={disabled}
                      className="text-muted-foreground hover:text-[#0A4D27]"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  )}
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeRow(index)}
                    disabled={disabled}
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            );
          })
        ) : (
          <p className="text-[10px] italic text-amber-700">Add at least one requisitioner (required).</p>
        )}
      </div>

      {listError && <p className="text-[11px] font-medium text-destructive">{listError}</p>}

      <Dialog
        open={isModalOpen}
        onOpenChange={(open) => {
          if (!open) {
            closeModal();
            return;
          }
          setIsModalOpen(true);
        }}
      >
        <DialogContent className="sm:max-w-[440px]">
          <DialogHeader>
            <DialogTitle>
              {draftReadOnly
                ? "Requisitioner Details"
                : editingIndex === null
                  ? "Add Requisitioner"
                  : "Edit Requisitioner"}
            </DialogTitle>
          </DialogHeader>

          {draftReadOnly && (
            <p className="text-sm text-muted-foreground">
              This requisitioner was selected from the directory. Remove it from the document to change the person tagged.
            </p>
          )}

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="requisitioner-employee" className="text-sm font-medium">
                Employee Number (optional)
              </Label>
              <Input
                id="requisitioner-employee"
                value={draft.employeeNumber}
                onChange={(event) => {
                  setDraft((current) => ({
                    ...current,
                    employeeNumber: formatEmployeeNumberInput(event.target.value),
                  }));
                  if (draftErrors.employeeNumber) {
                    setDraftErrors((current) => ({ ...current, employeeNumber: undefined }));
                  }
                }}
                placeholder={EMPLOYEE_NUMBER_PLACEHOLDER}
                autoComplete="off"
                spellCheck={false}
                disabled={
                  disabled ||
                  draftReadOnly ||
                  isManualRequisitionerEmployeeNumberLocked(
                    user?.role,
                    editingIndex !== null && !isDirectoryLinkedRequisitioner(draft)
                  )
                }
                className={cn(
                  "font-mono tracking-wide",
                  draftErrors.employeeNumber && "border-destructive focus-visible:ring-destructive"
                )}
              />
              <p className="text-xs text-muted-foreground">
                {draftReadOnly
                  ? "Employee number is managed in the Requisitioners Directory."
                  : `${EMPLOYEE_NUMBER_HELPER_TEXT}. Leave blank if the requisitioner is not an employee.`}
              </p>
              {draftErrors.employeeNumber && (
                <p className="text-sm text-destructive">{draftErrors.employeeNumber}</p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="requisitioner-first-name" className="text-sm font-medium">
                  First Name
                </Label>
                <Input
                  id="requisitioner-first-name"
                  value={draft.firstName}
                  onChange={(event) => {
                    setDraft((current) => ({ ...current, firstName: event.target.value }));
                    if (draftErrors.firstName) {
                      setDraftErrors((current) => ({ ...current, firstName: undefined }));
                    }
                  }}
                  onBlur={(event) =>
                    setDraft((current) => ({ ...current, firstName: formatPersonName(event.target.value) }))
                  }
                  placeholder="e.g. Juan"
                  disabled={disabled || draftReadOnly}
                  className={cn(draftErrors.firstName && "border-destructive focus-visible:ring-destructive")}
                />
                {draftErrors.firstName && (
                  <p className="text-sm text-destructive">{draftErrors.firstName}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="requisitioner-last-name" className="text-sm font-medium">
                  Last Name
                </Label>
                <Input
                  id="requisitioner-last-name"
                  value={draft.lastName}
                  onChange={(event) => {
                    setDraft((current) => ({ ...current, lastName: event.target.value }));
                    if (draftErrors.lastName) {
                      setDraftErrors((current) => ({ ...current, lastName: undefined }));
                    }
                  }}
                  onBlur={(event) =>
                    setDraft((current) => ({ ...current, lastName: formatPersonName(event.target.value) }))
                  }
                  placeholder="e.g. Dela Cruz"
                  disabled={disabled || draftReadOnly}
                  className={cn(draftErrors.lastName && "border-destructive focus-visible:ring-destructive")}
                />
                {draftErrors.lastName && (
                  <p className="text-sm text-destructive">{draftErrors.lastName}</p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium">Suffix</Label>
              <Select
                value={draft.suffix}
                disabled={disabled || draftReadOnly}
                onValueChange={(nextValue) => {
                  if (nextValue === null) return;
                  setDraft((current) => ({ ...current, suffix: nextValue }));
                  if (draftErrors.suffix) {
                    setDraftErrors((current) => ({ ...current, suffix: undefined }));
                  }
                }}
              >
                <SelectTrigger className="w-full" disabled={disabled || draftReadOnly}>
                  <SelectValue placeholder="No Suffix">
                    {suffixOptions.find((option) => option.value === draft.suffix)?.label || "No Suffix"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {suffixOptions.map((option) => (
                    <SelectItem key={option.value || "none"} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {draftErrors.suffix && <p className="text-sm text-destructive">{draftErrors.suffix}</p>}
            </div>
          </div>

          <DialogFooter>
            {draftReadOnly ? (
              <Button type="button" onClick={closeModal}>
                Close
              </Button>
            ) : (
              <>
                <Button type="button" variant="outline" onClick={closeModal}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={handleSaveRequisitioner}
                  disabled={isSavingRequisitioner}
                  className="bg-[#0A4D27] hover:bg-[#083E1D] text-white"
                >
                  {isSavingRequisitioner
                    ? "Saving..."
                    : editingIndex === null
                      ? "Add Requisitioner"
                      : "Save Changes"}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
