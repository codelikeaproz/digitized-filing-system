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

  // If orgUnitId is provided, only show categories for that orgUnit
  // Otherwise, show all
  const filteredCategories = orgUnitId 
    ? categories.filter(c => c.orgUnitId === orgUnitId) 
    : categories;

  const selectedCategory = categories.find(c => c.id === value);

  const handleAddCategory = async () => {
    if (!newCategoryName.trim()) return;
    
    // Admin needs an orgUnit if it wasn't provided
    const payloadOrgUnit = orgUnitId || targetOrgUnit;
    if (user?.role === 'admin' && !payloadOrgUnit) {
      return; // Handled by disabled button, but as a safeguard
    }

    setIsSubmitting(true);
    try {
      const newId = await addCategory(newCategoryName, payloadOrgUnit);
      if (newId) {
        onValueChange(newId);
        setIsAddModalOpen(false);
        setNewCategoryName("");
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
  };

  const handleCancelRenameCategory = () => {
    setEditingCategoryId(null);
    setEditingCategoryName("");
  };

  const handleRenameCategory = async () => {
    if (!editingCategoryId || !editingCategoryName.trim()) return;
    setIsSubmitting(true);
    try {
      const updated = await updateCategory(editingCategoryId, editingCategoryName);
      if (updated) {
        handleCancelRenameCategory();
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

      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Add New Category</DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            {user?.role === 'admin' && !orgUnitId && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Select target Org Unit</label>
                <Select value={targetOrgUnit} onValueChange={(val) => val !== null && setTargetOrgUnit(val)}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select Org Unit">
                      {targetOrgUnit ? (orgUnits.find(ou => ou.id === targetOrgUnit)?.name || "Select Org Unit...") : undefined}
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
                onChange={(e) => setNewCategoryName(e.target.value)}
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && handleAddCategory()}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddModalOpen(false)}>Cancel</Button>
            <Button 
              onClick={handleAddCategory} 
              disabled={!newCategoryName.trim() || isSubmitting || (user?.role === 'admin' && !orgUnitId && !targetOrgUnit)}
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
                const canDelete = user?.role === 'admin' || c.orgUnitId === user?.orgUnitId;
                const documentCount = getCategoryDocumentCount(c);
                const inUse = documentCount > 0;
                const documentLabel = `${documentCount} ${documentCount === 1 ? "document" : "documents"}`;
                
                return (
                  <div key={c.id} className="flex items-center justify-between gap-3 p-3 rounded-lg border bg-card/50">
                    <div className="flex min-w-0 flex-1 flex-col">
                      {editingCategoryId === c.id ? (
                        <Input
                          value={editingCategoryName}
                          onChange={(e) => setEditingCategoryName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleRenameCategory();
                            if (e.key === 'Escape') handleCancelRenameCategory();
                          }}
                          className="h-9"
                          autoFocus
                        />
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
