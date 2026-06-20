import { useCallback, useEffect, useState } from "react";
import { Eye, Loader2, Lock, MoreVertical, Pencil, Plus, Search, Trash2, UserRound } from "lucide-react";
import { toast } from "sonner";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RequisitionerDocumentsDialog } from "@/components/employees/RequisitionerDocumentsDialog";
import { PaginationControls } from "@/components/PaginationControls";
import { api, type PaginatedResponse } from "@/lib/api";
import { cn, formatPersonName } from "@/lib/utils";
import {
  formatEmployeeNumberInput,
  EMPLOYEE_NUMBER_PLACEHOLDER,
  EMPLOYEE_NUMBER_HELPER_TEXT,
  REQUISITIONERS_DIRECTORY_TITLE,
  validateOptionalEmployeeNumber,
  formatRequisitionerEmployeeNumberDisplay,
} from "@/lib/employee-number";
import { REQUISITIONER_SUFFIX_OPTIONS } from "@/lib/requisitioner";
import { useAuth } from "@/lib/auth-context";
import { canManageRequisitioners, canOverrideEmployeeNumberLock, EMPLOYEE_NUMBER_TAGGED_LOCK_HELPER, isEmployeeNumberLockedByTags } from "@/lib/requisitioner-permissions";
import type { EmployeeDirectoryEntry } from "@/types";

const emptyForm = {
  employeeNumber: "",
  firstName: "",
  lastName: "",
  suffix: "",
};

function getTaggedDocumentCount(employee: EmployeeDirectoryEntry, useScopedCount: boolean) {
  if (useScopedCount) {
    return employee.scopedReferencedDocumentCount ?? employee.referencedDocumentCount ?? 0;
  }
  return employee.referencedDocumentCount ?? 0;
}

function getDeleteDialogMessage(referenceCount: number) {
  if (referenceCount <= 3) return "";
  const documentLabel = referenceCount === 1 ? "document" : "documents";
  return (
    `Cannot delete requisitioner. This requisitioner is currently tagged on ${referenceCount} ${documentLabel}. ` +
    "Remove or update document tags before deletion."
  );
}

export default function EmployeeDirectoryPage() {
  const { user } = useAuth();
  const canManage = canManageRequisitioners(user?.role);
  const useScopedCount = !canManage;
  const [employees, setEmployees] = useState<EmployeeDirectoryEntry[]>([]);
  const [employeeCount, setEmployeeCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<EmployeeDirectoryEntry | null>(null);
  const [viewingEmployee, setViewingEmployee] = useState<EmployeeDirectoryEntry | null>(null);
  const [employeeToDelete, setEmployeeToDelete] = useState<EmployeeDirectoryEntry | null>(null);
  const [formData, setFormData] = useState(emptyForm);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [overrideMode, setOverrideMode] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [isOverrideDialogOpen, setIsOverrideDialogOpen] = useState(false);

  const resetEditState = () => {
    setOverrideMode(false);
    setOverrideReason("");
    setIsOverrideDialogOpen(false);
  };

  const editTaggedCount = editingEmployee ? getTaggedDocumentCount(editingEmployee, false) : 0;
  const isEmployeeNumberFieldLocked =
    !!editingEmployee &&
    isEmployeeNumberLockedByTags(editTaggedCount, editingEmployee.canChangeEmployeeNumber) &&
    !overrideMode;
  const employeeNumberHelperText = isEmployeeNumberFieldLocked
    ? editingEmployee?.employeeNumberBlockReason || EMPLOYEE_NUMBER_TAGGED_LOCK_HELPER
    : `${EMPLOYEE_NUMBER_HELPER_TEXT}. Leave blank if the requisitioner is not an employee.`;

  const fetchEmployees = useCallback(async (search = "", page = currentPage, size = pageSize) => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        activeOnly: "false",
        page,
        page_size: size,
      };
      if (search.trim()) params.search = search.trim();
      const data = await api.get<PaginatedResponse<EmployeeDirectoryEntry>>("/api/employees", params);
      setEmployees(data.results);
      setEmployeeCount(data.count);
    } catch (error: any) {
      toast.error(error.message || "Failed to load requisitioners");
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setCurrentPage(1);
  };

  useEffect(() => {
    document.title = `${REQUISITIONERS_DIRECTORY_TITLE} | DigiFile`;
    return () => {
      document.title = "DigiFile";
    };
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  useEffect(() => {
    const timer = setTimeout(() => fetchEmployees(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [fetchEmployees, searchQuery, currentPage, pageSize]);

  const openCreateModal = () => {
    setEditingEmployee(null);
    setFormData(emptyForm);
    resetEditState();
    setIsModalOpen(true);
  };

  const openEditModal = (employee: EmployeeDirectoryEntry) => {
    setEditingEmployee(employee);
    setFormData({
      employeeNumber: employee.employeeNumber,
      firstName: employee.firstName,
      lastName: employee.lastName,
      suffix: employee.suffix || "",
    });
    resetEditState();
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    const firstName = formatPersonName(formData.firstName.trim());
    const lastName = formatPersonName(formData.lastName.trim());
    let employeeNumber = formData.employeeNumber.trim();

    if (editingEmployee && isEmployeeNumberFieldLocked) {
      employeeNumber = editingEmployee.employeeNumber || "";
    }

    const employeeNumberError = validateOptionalEmployeeNumber(employeeNumber);

    if (employeeNumberError) {
      toast.error(employeeNumberError);
      return;
    }
    if (!firstName || !lastName) {
      toast.error("First name and last name are required.");
      return;
    }

    setIsSaving(true);
    try {
      const payload: Record<string, string | boolean> = {
        employeeNumber: employeeNumber ? formatEmployeeNumberInput(employeeNumber) : "",
        firstName,
        lastName,
        suffix: formData.suffix,
        isActive: true,
      };

      if (editingEmployee) {
        if (overrideMode && overrideReason.trim()) {
          payload.employeeNumberOverrideReason = overrideReason.trim();
        }
        await api.put(`/api/employees/${editingEmployee.id}`, payload);
        toast.success("Requisitioner updated");
      } else {
        await api.post("/api/employees/upsert", payload);
        toast.success("Requisitioner added");
      }

      setIsModalOpen(false);
      resetEditState();
      fetchEmployees(searchQuery);
    } catch (error: any) {
      toast.error(error.message || "Failed to save requisitioner");
    } finally {
      setIsSaving(false);
    }
  };

  const handleConfirmOverride = () => {
    const reason = overrideReason.trim();
    if (!reason) {
      toast.error("A reason is required to override the employee number lock.");
      return;
    }
    setOverrideMode(true);
    setIsOverrideDialogOpen(false);
  };

  const handleDelete = async () => {
    if (!employeeToDelete) return;
    setIsDeleting(true);
    try {
      await api.delete(`/api/employees/${employeeToDelete.id}`);
      toast.success("Requisitioner deleted");
      setEmployeeToDelete(null);
      fetchEmployees(searchQuery);
    } catch (error: any) {
      toast.error(error.message || "Failed to delete requisitioner");
    } finally {
      setIsDeleting(false);
    }
  };

  const deleteReferenceCount = employeeToDelete?.referencedDocumentCount ?? 0;
  const canConfirmDelete = employeeToDelete ? employeeToDelete.canDelete !== false : false;

  return (
    <div className="p-6 space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#112217]">{REQUISITIONERS_DIRECTORY_TITLE}</h1>
            <p className="text-gray-500 mt-1">
              {canManage
                ? "Maintain requisitioner records used when searching on document upload and edit."
                : "Browse requisitioner records and tagged documents within your office unit scope. Directory changes are managed by administrators."}
            </p>
          </div>
          {canManage && (
          <Button onClick={openCreateModal} className="bg-[#0A4D27] hover:bg-[#083E1D] text-white">
              <Plus className="mr-2 h-4 w-4" />
              Add Requisitioner
          </Button>
          )}
        </div>

        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search requisitioners by number or name..."
            className="pl-9"
          />
        </div>

        <div className="rounded-md border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Requisitioner No.</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Tagged Documents</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
                  </TableCell>
                </TableRow>
              ) : employees.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                    No requisitioners found.
                  </TableCell>
                </TableRow>
              ) : (
                employees.map((employee) => {
                  const deleteDisabled = employee.canDelete === false;
                  const taggedCount = getTaggedDocumentCount(employee, useScopedCount);
                  return (
                    <TableRow key={employee.id}>
                      <TableCell className="font-mono text-sm">
                        {formatRequisitionerEmployeeNumberDisplay(employee.employeeNumber)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <UserRound className="h-4 w-4 text-muted-foreground" />
                          <span>{employee.fullName}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        Tagged Documents:{" "}
                        <span className="font-medium text-foreground">{taggedCount}</span>
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            className={cn(buttonVariants({ variant: "ghost" }), "h-8 w-8 p-0")}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setViewingEmployee(employee)}>
                              <Eye className="mr-2 h-4 w-4 text-blue-600" />
                              View Documents
                            </DropdownMenuItem>
                            {canManage && (
                              <>
                            <DropdownMenuItem onClick={() => openEditModal(employee)}>
                              <Pencil className="mr-2 h-4 w-4 text-blue-600" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                  disabled={deleteDisabled}
                                  className="text-destructive focus:text-destructive"
                                  title={
                                    deleteDisabled
                                      ? employee.deleteBlockReason ||
                                        "Cannot delete. Tagged on more than 3 documents."
                                      : undefined
                                  }
                                  onClick={() => {
                                    if (!deleteDisabled) setEmployeeToDelete(employee);
                                  }}
                                >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                              </>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
          <PaginationControls
            count={employeeCount}
            currentPage={currentPage}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={handlePageSizeChange}
            disabled={loading}
          />
        </div>

        <RequisitionerDocumentsDialog
          employee={viewingEmployee}
          open={!!viewingEmployee}
          onOpenChange={(open) => !open && setViewingEmployee(null)}
        />

        <Dialog
          open={isModalOpen}
          onOpenChange={(open) => {
            setIsModalOpen(open);
            if (!open) resetEditState();
          }}
        >
            <DialogContent className="sm:max-w-[440px]">
              <DialogHeader>
                <DialogTitle>{editingEmployee ? "Edit Requisitioner" : "Add Requisitioner"}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-2">
                {editingEmployee && (
                  <div className="rounded-lg border bg-muted/20 px-3 py-2 text-sm">
                    <span className="text-muted-foreground">Tagged Documents: </span>
                    <span className="font-medium text-foreground">{editTaggedCount}</span>
                  </div>
                )}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="employee-number">Employee Number (optional)</Label>
                    {isEmployeeNumberFieldLocked && (
                      <Lock className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                    )}
                  </div>
                  <Input
                    id="employee-number"
                    value={formData.employeeNumber}
                    onChange={(event) =>
                      setFormData((current) => ({
                        ...current,
                        employeeNumber: formatEmployeeNumberInput(event.target.value),
                      }))
                    }
                    placeholder={EMPLOYEE_NUMBER_PLACEHOLDER}
                    className="font-mono tracking-wide"
                    autoComplete="off"
                    spellCheck={false}
                    disabled={isEmployeeNumberFieldLocked}
                  />
                  <p className="text-xs text-muted-foreground">{employeeNumberHelperText}</p>
                  {editingEmployee &&
                    isEmployeeNumberLockedByTags(editTaggedCount, editingEmployee.canChangeEmployeeNumber) &&
                    canOverrideEmployeeNumberLock(user?.role) &&
                    !overrideMode && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setIsOverrideDialogOpen(true)}
                      >
                        Override employee number lock
                      </Button>
                    )}
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="employee-first-name">First Name</Label>
                    <Input
                      id="employee-first-name"
                      value={formData.firstName}
                      onChange={(event) => setFormData((current) => ({ ...current, firstName: event.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="employee-last-name">Last Name</Label>
                    <Input
                      id="employee-last-name"
                      value={formData.lastName}
                      onChange={(event) => setFormData((current) => ({ ...current, lastName: event.target.value }))}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Suffix</Label>
                  <Select
                    value={formData.suffix}
                    onValueChange={(value) => value !== null && setFormData((current) => ({ ...current, suffix: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="No Suffix" />
                    </SelectTrigger>
                    <SelectContent>
                      {REQUISITIONER_SUFFIX_OPTIONS.map((option) => (
                        <SelectItem key={option.value || "none"} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsModalOpen(false)} disabled={isSaving}>
                  Cancel
                </Button>
                <Button onClick={handleSave} disabled={isSaving} className="bg-[#0A4D27] hover:bg-[#083E1D] text-white">
                  {isSaving ? "Saving..." : editingEmployee ? "Save Changes" : "Add Requisitioner"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

        <AlertDialog open={isOverrideDialogOpen} onOpenChange={setIsOverrideDialogOpen}>
          <AlertDialogContent className="sm:max-w-md">
            <AlertDialogHeader>
              <AlertDialogTitle>Override employee number lock</AlertDialogTitle>
              <AlertDialogDescription>
                This requisitioner is tagged on {editTaggedCount} document
                {editTaggedCount === 1 ? "" : "s"}. Changing the employee number requires a documented reason and will be
                recorded in the audit log.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <div className="space-y-2">
              <Label htmlFor="override-reason">Reason</Label>
              <Textarea
                id="override-reason"
                value={overrideReason}
                onChange={(event) => setOverrideReason(event.target.value)}
                placeholder="Explain why the employee number must be changed..."
                rows={4}
              />
            </div>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={(event) => {
                  event.preventDefault();
                  handleConfirmOverride();
                }}
                className="bg-[#0A4D27] text-white hover:bg-[#083E1D] hover:text-white"
              >
                Enable editing
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <AlertDialog open={!!employeeToDelete} onOpenChange={(open) => !open && !isDeleting && setEmployeeToDelete(null)}>
          <AlertDialogContent className="sm:max-w-md">
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Requisitioner</AlertDialogTitle>
              <AlertDialogDescription>
                {canConfirmDelete
                  ? "This will remove the requisitioner from the directory. Document tags on existing files are not changed."
                  : "This requisitioner cannot be deleted while tagged on too many documents."}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <div className="space-y-3 rounded-lg border bg-muted/30 p-4 text-sm">
              <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3">
                <div className="text-muted-foreground">Requisitioner Number</div>
                <div className="font-medium text-foreground">
                  {formatRequisitionerEmployeeNumberDisplay(employeeToDelete?.employeeNumber)}
                </div>
                <div className="text-muted-foreground">Name</div>
                <div className="font-medium text-foreground">{employeeToDelete?.fullName}</div>
                <div className="text-muted-foreground">Tagged Documents</div>
                <div className="font-medium text-foreground">{deleteReferenceCount}</div>
              </div>
              {!canConfirmDelete && (
                <p className="border-t pt-3 text-destructive">{getDeleteDialogMessage(deleteReferenceCount)}</p>
              )}
            </div>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                disabled={!canConfirmDelete || isDeleting}
                onClick={(event) => {
                  event.preventDefault();
                  handleDelete();
                }}
                className="bg-red-600 text-white hover:bg-red-700 hover:text-white focus:ring-red-600 disabled:opacity-50"
              >
                {isDeleting ? "Deleting..." : "Delete Requisitioner"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
    </div>
  );
}
