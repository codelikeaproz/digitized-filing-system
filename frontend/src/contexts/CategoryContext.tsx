// Version 1.0.2 - API Integration Robustness
import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { logAudit } from "@/lib/audit";

interface Category {
  id: string;
  name: string;
  org_unit?: number | null;
  orgUnitId?: string;
  inUse?: boolean;
  document_count?: number;
  documentCount?: number;
}

interface CategoryContextType {
  categories: Category[];
  loading: boolean;
  addCategory: (name: string, orgUnitId?: string) => Promise<string | null>;
  updateCategory: (id: string, name: string) => Promise<boolean>;
  deleteCategory: (id: string) => Promise<boolean>;
  refreshCategories: (orgUnitId?: string) => Promise<void>;
}

const CategoryContext = createContext<CategoryContextType | undefined>(undefined);

export function CategoryProvider({ children }: { children: React.ReactNode }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCategories = useCallback(async (orgUnitId?: string) => {
    setLoading(true);
    try {
      const query = orgUnitId ? `?orgUnitId=${orgUnitId}` : '';
      const data = await api.get<Category[]>(`/api/categories${query}`);
      setCategories(data);
    } catch (error: any) {
      console.error("API Category Fetch Error:", error);
      toast.error(`Failed to load categories: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const addCategory = useCallback(async (name: string, orgUnitId?: string) => {
    const trimmedName = name.trim();
    if (!trimmedName) return null;

    try {
      const payload: any = { name: trimmedName };
      if (orgUnitId) payload.orgUnitId = orgUnitId;
      
      const newCategory = await api.post<Category>("/api/categories", payload);
      setCategories(prev => [...prev, newCategory].sort((a, b) => a.name.localeCompare(b.name)));
      toast.success(`Category "${newCategory.name}" added.`);
      return newCategory.id;
    } catch (error: any) {
      console.error("Error adding category:", error);
      toast.error(error.message || "Failed to add category");
      return null;
    }
  }, []);

  const updateCategory = useCallback(async (id: string, name: string) => {
    const trimmedName = name.trim();
    if (!trimmedName) return false;

    try {
      const existingCategory = categories.find(c => c.id === id);
      const updatedCategory = await api.put<Category>(`/api/categories/${id}`, { name: trimmedName });
      setCategories(prev => prev.map(c => c.id === id ? updatedCategory : c).sort((a, b) => a.name.localeCompare(b.name)));
      
      await logAudit(
        "UPDATE_CATEGORY", 
        `Updated Category: ${existingCategory?.name || 'Unknown'} → ${trimmedName}`,
        undefined,
        'category',
        trimmedName
      );

      toast.success(`Category renamed to "${updatedCategory.name}".`);
      return true;
    } catch (error: any) {
      console.error("Error updating category:", error);
      toast.error(error.message || "Failed to update category");
      return false;
    }
  }, [categories]);

  const deleteCategory = useCallback(async (id: string) => {
    try {
      await api.delete(`/api/categories/${id}`);
      setCategories(prev => prev.filter(c => c.id !== id));

      toast.success(`Category deleted successfully.`);
      return true;
    } catch (error: any) {
      console.error("Error deleting category:", error);
      toast.error(error.message || "Failed to delete category");
      return false;
    }
  }, [categories]);

  return (
    <CategoryContext.Provider value={{ categories, loading, addCategory, updateCategory, deleteCategory, refreshCategories: fetchCategories }}>
      {children}
    </CategoryContext.Provider>
  );
}

export function useCategories() {
  const context = useContext(CategoryContext);
  if (context === undefined) {
    throw new Error("useCategories must be used within a CategoryProvider");
  }
  return context;
}
