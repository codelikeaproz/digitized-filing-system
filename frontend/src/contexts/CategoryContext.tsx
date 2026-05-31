// Version 1.0.2 - API Integration Robustness
import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { api, PaginatedResponse } from "@/lib/api";
import type { Category } from "@/types";

interface CategoryContextType {
  categories: Category[];
  loading: boolean;
  addCategory: (name: string, orgUnitId?: string) => Promise<{ id: string | null; duplicate: boolean }>;
  updateCategory: (id: string, name: string) => Promise<{ ok: boolean; duplicate: boolean }>;
  deleteCategory: (id: string) => Promise<boolean>;
  refreshCategories: (orgUnitId?: string) => Promise<void>;
}

const CategoryContext = createContext<CategoryContextType | undefined>(undefined);

function normalizeCategory(category: Category): Category {
  const rawOrgUnitId = category.orgUnitId ?? category.org_unit;

  return {
    ...category,
    id: String(category.id),
    orgUnitId: rawOrgUnitId === undefined || rawOrgUnitId === null ? null : String(rawOrgUnitId),
  };
}

export function CategoryProvider({ children }: { children: React.ReactNode }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCategories = useCallback(async (orgUnitId?: string) => {
    setLoading(true);
    try {
      const data = await api.get<Category[] | PaginatedResponse<Category>>(
        "/api/categories",
        orgUnitId ? { orgUnitId } : undefined
      );
      const categoryList = Array.isArray(data) ? data : data.results;
      setCategories(categoryList.map(normalizeCategory));
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
    if (!trimmedName) return { id: null, duplicate: false };

    try {
      const payload: Record<string, string> = { name: trimmedName };
      if (orgUnitId) {
        payload.orgUnitId = orgUnitId;
      }
      
      const newCategory = normalizeCategory(await api.post<Category>("/api/categories", payload));
      setCategories(prev => [...prev, newCategory].sort((a, b) => a.name.localeCompare(b.name)));
      toast.success(`Category "${newCategory.name}" added.`);
      return { id: newCategory.id, duplicate: false };
    } catch (error: any) {
      console.error("Error adding category:", error);
      const message = error.message || "Failed to add category";
      const duplicate = /already exists/i.test(message);
      toast.error(message);
      return { id: null, duplicate };
    }
  }, []);

  const updateCategory = useCallback(async (id: string, name: string) => {
    const trimmedName = name.trim();
    if (!trimmedName) return { ok: false, duplicate: false };

    try {
      const updatedCategory = normalizeCategory(await api.put<Category>(`/api/categories/${id}`, { name: trimmedName }));
      setCategories(prev => prev.map(c => c.id === id ? updatedCategory : c).sort((a, b) => a.name.localeCompare(b.name)));

      toast.success(`Category renamed to "${updatedCategory.name}".`);
      return { ok: true, duplicate: false };
    } catch (error: any) {
      console.error("Error updating category:", error);
      const message = error.message || "Failed to update category";
      const duplicate = /already exists/i.test(message);
      toast.error(message);
      return { ok: false, duplicate };
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
