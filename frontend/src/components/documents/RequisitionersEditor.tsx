import { useMemo, useState } from "react";
import { Pencil, Plus, Trash2, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { formatRequisitionerEmployeeNumberDisplay, sanitizeEmployeeNumberInput } from "@/lib/employee-number";
import {
  buildRequisitionerFullName,
  createEmptyRequisitioner,
  normalizeRequisitionerInput,
  REQUISITIONER_SUFFIX_OPTIONS,
  type RequisitionerInput,
  type RequisitionerRowErrors,
  validateSingleRequisitioner,
} from "@/lib/requisitioner";

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
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [draft, setDraft] = useState<RequisitionerInput>(createEmptyRequisitioner());
  const [draftErrors, setDraftErrors] = useState<RequisitionerRowErrors>({});

  const suffixOptions = useMemo(() => {
    const options = REQUISITIONER_SUFFIX_OPTIONS.map((option) => ({ ...option }));
    if (draft.suffix && !options.some((option) => option.value === draft.suffix)) {
      options.push({ value: draft.suffix, label: draft.suffix });
    }
    return options;
  }, [draft.suffix]);

  const resetDraft = () => {
    setDraft(createEmptyRequisitioner());
    setDraftErrors({});
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
    setEditingIndex(index);
    setDraft({ ...value[index] });
    setDraftErrors({});
    setIsModalOpen(true);
  };

  const removeRow = (index: number) => {
    onChange(value.filter((_, rowIndex) => rowIndex !== index));
  };

  const handleSaveRequisitioner = () => {
    const validation = validateSingleRequisitioner(draft, value, editingIndex ?? undefined);
    setDraftErrors(validation.errors);
    if (!validation.isValid) {
      return;
    }

    const normalized = normalizeRequisitionerInput(draft);
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
          Add
        </Button>
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
            <DialogTitle>{editingIndex === null ? "Add Requisitioner" : "Edit Requisitioner"}</DialogTitle>
          </DialogHeader>

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
                    employeeNumber: sanitizeEmployeeNumberInput(event.target.value),
                  }));
                  if (draftErrors.employeeNumber) {
                    setDraftErrors((current) => ({ ...current, employeeNumber: undefined }));
                  }
                }}
                placeholder="e.g. 202400123"
                autoFocus
                className={cn(
                  draftErrors.employeeNumber && "border-destructive focus-visible:ring-destructive"
                )}
              />
              <p className="text-xs text-muted-foreground">
                Leave blank if the requisitioner is not an employee.
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
                onValueChange={(nextValue) => {
                  if (nextValue === null) return;
                  setDraft((current) => ({ ...current, suffix: nextValue }));
                  if (draftErrors.suffix) {
                    setDraftErrors((current) => ({ ...current, suffix: undefined }));
                  }
                }}
              >
                <SelectTrigger className="w-full">
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
            <Button type="button" variant="outline" onClick={closeModal}>
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleSaveRequisitioner}
              className="bg-[#0A4D27] hover:bg-[#083E1D] text-white"
            >
              {editingIndex === null ? "Add Requisitioner" : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
