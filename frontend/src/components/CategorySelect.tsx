/**
 * CategorySelect — category picker with inline create (uses CategoryContext).
 * APIs: GET/POST /api/categories via CategoryContext.
 */
import React, { useState, useEffect } from "react";
import { 
  X, 
  Plus,
  Pencil,
  Check,
  ChevronDown,
  Filter,
  PlusCircle,
  Settings2,
  Trash2,
  AlertTriangle
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectSeparator,
} from "@/components/ui/select";
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCategories } from "@/contexts/CategoryContext";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { PaginatedResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { Category } from "@/types";

interface CategorySelectProps {
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  showAllOption?: boolean;
  orgUnitId?: string; // Optional context limit
}

export function CategorySelect({ 
  value, 
  onValueChange, 
  placeholder = "Select category...", 
  className,
  showAllOption = false,
  orgUnitId
}: CategorySelectProps) {
  const { categories, addCategory, updateCategory, deleteCategory } = useCategories();
  const { user } = useAuth();
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isManageModalOpen, setIsManageModalOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [targetOrgUnit, setTargetOrgUnit] = useState<string>(orgUnitId || "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [editingCategoryName, setEditingCategoryName] = useState("");

  const [orgUnits, setOrgUnits] = useState<{id: string, name: string}[]>([]);
  const [categoryToDelete, setCategoryToDelete] = useState<Category | null>(null);
  const [addCategoryNameError, setAddCategoryNameError] = useState(false);
  const [renameCategoryNameError, setRenameCategoryNameError] = useState(false);

  const getPayloadOrgUnit = () => {
    if (orgUnitId) return orgUnitId;
    if (targetOrgUnit) return targetOrgUnit;
    if (user?.role !== "admin" && user?.orgUnitId) return String(user.orgUnitId);
    return "";
  };

  const isDuplicateCategoryName = (
    name: string,
    payloadOrgUnit?: string,
    excludeId?: string
  ) => {
    const normalizedName = name.trim().toLowerCase();
    if (!normalizedName) return false;

    return categories.some(
      (category) =>
        category.id !== excludeId &&
        category.name.trim().toLowerCase() === normalizedName &&
        String(category.orgUnitId ?? "") === String(payloadOrgUnit ?? "")
    );
  };

  const duplicateCategoryMessage = "A category with this name already exists in this Office Unit.";

  useEffect(() => {
    if (orgUnitId) {
      setTargetOrgUnit(orgUnitId);
    }
  }, [orgUnitId]);

  useEffect(() => {
    // If admin and no orgUnit is forced, fetch org units to populate the selection and labels
    // Do it once so we have names
    if (user?.role === 'admin' && !orgUnitId) {
      api.get<PaginatedResponse<{id: string, name: string}>>('/api/org-units/', { page_size: 100 })
        .then(res => setOrgUnits(res.results))
        .catch(console.error);
    }
  }, [user?.role, orgUnitId]);

  // Staff / Dept Head never see global (unassigned) categories.
  const filteredCategories = orgUnitId
    ? categories.filter((c) => String(c.orgUnitId ?? "") === String(orgUnitId))
    : user?.role === "admin"
      ? categories
      : categories.filter((c) => c.orgUnitId != null && c.orgUnitId !== "");

  const selectedCategory = categories.find(c => c.id === value);

  const handleAddCategory = async () => {
    if (!newCategoryName.trim()) return;
    
    if (user?.role !== "admin" && !getPayloadOrgUnit()) {
      toast.error("Your account must be assigned to an Office Unit to create categories.");
      return;
    }

    const payloadOrgUnit = getPayloadOrgUnit();
    if (user?.role === "admin" && !payloadOrgUnit) {
      return;
    }

    const normalizedName = newCategoryName.trim();
    if (isDuplicateCategoryName(normalizedName, payloadOrgUnit)) {
      setAddCategoryNameError(true);
      toast.error(`"${normalizedName}" already exists in this Office Unit.`);
      return;
    }

    setAddCategoryNameError(false);
    setIsSubmitting(true);
    try {
      const result = await addCategory(newCategoryName, payloadOrgUnit);
      if (result.id) {
        onValueChange(result.id);
        setIsAddModalOpen(false);
        setNewCategoryName("");
        setAddCategoryNameError(false);
      } else if (result.duplicate) {
        setAddCategoryNameError(true);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const getCategoryLabel = (c: Category) => {
    if (user?.role === 'admin' && !orgUnitId) {
      // Find the org unit name if we fetched them, else just show ID or fallback
      // Since we don't always fetch org units unless adding, we can try to find from existing
      return `${c.name} — ${orgUnits.find(ou => ou.id === c.orgUnitId)?.name || (c.orgUnitId ? 'OrgUnit ' + c.orgUnitId.slice(-4) : 'Global')}`;
    }
    return c.name;
  };

  const handleDeleteCategory = async () => {
    if (!categoryToDelete) return;
    setIsSubmitting(true);
    try {
      await deleteCategory(categoryToDelete.id);
      if (value === categoryToDelete.id) {
        onValueChange('');
      }
      setCategoryToDelete(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartRenameCategory = (category: Category) => {
    setEditingCategoryId(category.id);
    setEditingCategoryName(category.name);
    setRenameCategoryNameError(false);
  };

  const handleCancelRenameCategory = () => {
    setEditingCategoryId(null);
    setEditingCategoryName("");
    setRenameCategoryNameError(false);
  };

  const handleRenameCategory = async () => {
    if (!editingCategoryId || !editingCategoryName.trim()) return;

    const currentCategory = categories.find((category) => category.id === editingCategoryId);
    const normalizedName = editingCategoryName.trim();
    if (isDuplicateCategoryName(normalizedName, currentCategory?.orgUnitId ?? undefined, editingCategoryId)) {
      setRenameCategoryNameError(true);
      toast.error(`"${normalizedName}" already exists in this Office Unit.`);
      return;
    }

    setRenameCategoryNameError(false);
    setIsSubmitting(true);
    try {
      const result = await updateCategory(editingCategoryId, editingCategoryName);
      if (result.ok) {
        handleCancelRenameCategory();
      } else if (result.duplicate) {
        setRenameCategoryNameError(true);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const getCategoryDocumentCount = (category: Category) => {
    return category.document_count ?? category.documentCount ?? 0;
  };

  const handleRequestDeleteCategory = (category: Category) => {
    const inUse = getCategoryDocumentCount(category) > 0;
    if (inUse) return;
    setCategoryToDelete(category);
  };

  return (
    <>
      <Select 
        value={value} 
        onValueChange={(val) => {
          if (val === null) return;
          if (val === "ADD_NEW") {
            setAddCategoryNameError(false);
            setIsAddModalOpen(true);
          } else if (val === "MANAGE_CATEGORIES") {
            setIsManageModalOpen(true);
          } else {
            onValueChange(val);
          }
        }}
      >
        <SelectTrigger className={cn("h-10", className)}>
          <SelectValue placeholder={placeholder}>
            {showAllOption && value === "all" ? "All Categories" : (selectedCategory ? getCategoryLabel(selectedCategory) : undefined)}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {showAllOption && (
            <SelectItem value="all">
              <span className="flex items-center gap-2">
                <Filter className="h-4 w-4" />
                All Categories
              </span>
            </SelectItem>
          )}
          {filteredCategories.map((c) => (
            <SelectItem key={c.id} value={c.id}>
              {getCategoryLabel(c)}
            </SelectItem>
          ))}
          <SelectSeparator />
          <SelectItem value="ADD_NEW" className="text-primary font-medium focus:text-primary">
            <span className="flex items-center gap-2">
              <PlusCircle className="h-4 w-4" />
              Add New Category
            </span>
          </SelectItem>
          <SelectItem value="MANAGE_CATEGORIES" className="text-muted-foreground font-medium focus:text-foreground">
            <span className="flex items-center gap-2">
              <Settings2 className="h-4 w-4" />
              Manage Categories
            </span>
          </SelectItem>
        </SelectContent>
      </Select>

      <Dialog
        open={isAddModalOpen}
        onOpenChange={(open) => {
          setIsAddModalOpen(open);
          if (!open) {
            setNewCategoryName("");
            setAddCategoryNameError(false);
          }
        }}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Add New Category</DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            {user?.role === 'admin' && !orgUnitId && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Select target Office Unit</label>
                <Select value={targetOrgUnit} onValueChange={(val) => val !== null && setTargetOrgUnit(val)}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select Office Unit">
                      {targetOrgUnit ? (orgUnits.find(ou => ou.id === targetOrgUnit)?.name || "Select Office Unit...") : undefined}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {orgUnits.map(ou => (
                      <SelectItem key={ou.id} value={ou.id}>{ou.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium">Category Name</label>
              <Input 
                placeholder="e.g. Legal, HR, Finance" 
                value={newCategoryName}
                onChange={(e) => {
                  setNewCategoryName(e.target.value);
                  if (addCategoryNameError) setAddCategoryNameError(false);
                }}
                autoFocus
                aria-invalid={addCategoryNameError}
                onKeyDown={(e) => e.key === 'Enter' && handleAddCategory()}
                className={cn(
                  addCategoryNameError && "border-destructive focus-visible:border-destructive focus-visible:ring-destructive/30"
                )}
              />
              {addCategoryNameError && (
                <p className="text-sm text-destructive">{duplicateCategoryMessage}</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddModalOpen(false)}>Cancel</Button>
            <Button 
              onClick={handleAddCategory} 
              disabled={
                !newCategoryName.trim() ||
                isSubmitting ||
                (user?.role === "admin" && !orgUnitId && !targetOrgUnit) ||
                (user?.role !== "admin" && !getPayloadOrgUnit())
              }
            >
              {isSubmitting ? "Creating..." : "Create Category"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Manage Categories Dialog */}
      <Dialog open={isManageModalOpen} onOpenChange={setIsManageModalOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Manage Categories</DialogTitle>
          </DialogHeader>
          <div className="py-4 max-h-[60vh] overflow-y-auto space-y-2 pr-2">
            {filteredCategories.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                No categories available.
              </div>
            ) : (
              filteredCategories.map(c => {
                const canDelete =
                  user?.role === "admin" ||
                  String(c.orgUnitId ?? "") === String(user?.orgUnitId ?? "");
                const documentCount = getCategoryDocumentCount(c);
                const inUse = documentCount > 0;
                const documentLabel = `${documentCount} ${documentCount === 1 ? "document" : "documents"}`;
                
                return (
                  <div key={c.id} className="flex items-center justify-between gap-3 p-3 rounded-lg border bg-card/50">
                    <div className="flex min-w-0 flex-1 flex-col">
                      {editingCategoryId === c.id ? (
                        <>
                          <Input
                            value={editingCategoryName}
                            onChange={(e) => {
                              setEditingCategoryName(e.target.value);
                              if (renameCategoryNameError) setRenameCategoryNameError(false);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleRenameCategory();
                              if (e.key === 'Escape') handleCancelRenameCategory();
                            }}
                            aria-invalid={renameCategoryNameError}
                            className={cn(
                              "h-9",
                              renameCategoryNameError &&
                                "border-destructive focus-visible:border-destructive focus-visible:ring-destructive/30"
                            )}
                            autoFocus
                          />
                          {renameCategoryNameError && (
                            <p className="mt-1 text-xs text-destructive">{duplicateCategoryMessage}</p>
                          )}
                        </>
                      ) : (
                        <span className="font-medium text-sm truncate">{c.name}</span>
                      )}
                      <span className="text-xs text-muted-foreground mt-1">
                        {documentLabel}
                      </span>
                      {user?.role === 'admin' && !orgUnitId && (
                        <span className="text-xs text-muted-foreground mt-0.5">
                          {orgUnits.find(ou => ou.id === c.orgUnitId)?.name || 'Global'}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {editingCategoryId === c.id ? (
                        <>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={handleRenameCategory}
                            disabled={isSubmitting || !editingCategoryName.trim()}
                            className="text-[#0A4D27] hover:text-[#0A4D27] hover:bg-[#0A4D27]/10"
                          >
                            <Check className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={handleCancelRenameCategory} disabled={isSubmitting}>
                            <X className="h-4 w-4" />
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleStartRenameCategory(c)}
                          disabled={!canDelete}
                          className="text-muted-foreground hover:text-[#0A4D27]"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      )}
                      {inUse ? (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger render={<div className="flex items-center gap-2" />}>
                                <span className="inline-block cursor-not-allowed">
                                  <Button
                                    variant="ghost" 
                                    size="icon"
                                    disabled={true}
                                    className="text-muted-foreground pointer-events-none"
                                    render={<div />}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </span>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Cannot delete category because it is used by documents.</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      ) : (
                        <Button
                          variant="ghost" 
                          size="icon"
                          disabled={!canDelete}
                          className={canDelete ? "text-destructive hover:text-destructive hover:bg-destructive/10" : ""}
                          onClick={() => handleRequestDeleteCategory(c)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
          <DialogFooter>
            <Button variant="default" className="bg-[#0A4D27] hover:bg-[#0A4D27]/90" onClick={() => setIsManageModalOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!categoryToDelete} onOpenChange={(open) => !open && setCategoryToDelete(null)}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Delete Category
            </DialogTitle>
            <DialogDescription className="pt-2">
              Are you sure you want to delete this category? This action cannot be undone.
              <br/><br/>
              <span className="font-semibold text-foreground text-base border-l-2 border-destructive pl-2 py-0.5 block">{categoryToDelete?.name}</span>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setCategoryToDelete(null)}>Cancel</Button>
            <Button 
              variant="destructive"
              onClick={handleDeleteCategory} 
              disabled={isSubmitting}
            >
              {isSubmitting ? "Deleting..." : "Delete Category"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
