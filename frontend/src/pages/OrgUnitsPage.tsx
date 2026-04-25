import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { Network, Plus, Trash2, Edit, Loader2, FolderTree } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/auth-context';
import { logAudit } from '@/lib/audit';
import { PaginationControls } from '@/components/PaginationControls';
import { PaginatedResponse } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

type OrgUnit = {
  id: string;
  name: string;
  parentId: string | null;
  type: string | null;
  createdAt: string;
};

export default function OrgUnitsPage() {
  const [orgUnits, setOrgUnits] = useState<OrgUnit[]>([]);
  const [allOrgUnits, setAllOrgUnits] = useState<OrgUnit[]>([]);
  const [orgUnitCount, setOrgUnitCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(true);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [formData, setFormData] = useState({ name: '', parentId: '', type: 'Department' });
  const [ouToDelete, setOuToDelete] = useState<OrgUnit | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const { user: currentUser } = useAuth();
  const isAdmin = currentUser?.role === 'admin';

  const fetchOrgUnits = async () => {
    try {
      setIsLoading(true);
      const data = await api.get<PaginatedResponse<OrgUnit>>('/api/org-units/', {
        page: currentPage,
        page_size: pageSize,
      });
      setOrgUnits(data.results);
      setOrgUnitCount(data.count);
    } catch (error: any) {
      toast.error(error.message || 'Failed to fetch org units');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAllOrgUnits = async () => {
    try {
      const data = await api.get<PaginatedResponse<OrgUnit>>('/api/org-units/', { page_size: 100 });
      setAllOrgUnits(data.results);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchOrgUnits();
  }, [currentPage, pageSize]);

  useEffect(() => {
    fetchAllOrgUnits();
  }, []);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setCurrentPage(1);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleOpenAdd = () => {
    setFormData({ name: '', parentId: '', type: 'Department' });
    setIsEditMode(false);
    setEditId(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (ou: OrgUnit) => {
    setFormData({ name: ou.name, parentId: ou.parentId || '', type: ou.type || 'Department' });
    setIsEditMode(true);
    setEditId(ou.id);
    setIsModalOpen(true);
  };

  const handleDelete = async () => {
    if (!ouToDelete) return;
    setIsDeleting(true);
    try {
      await api.delete(`/api/org-units/${ouToDelete.id}/`);
      await fetchOrgUnits();
      await fetchAllOrgUnits();
      toast.success('Org Unit deleted successfully');
      setOuToDelete(null);
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete org unit');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEditMode && editId) {
        const updatedOu = await api.put<OrgUnit>(`/api/org-units/${editId}/`, {
          ...formData,
          parentId: formData.parentId || null,
          type: formData.type || null
        });
        await fetchOrgUnits();
        await fetchAllOrgUnits();
        
        await logAudit(
          'UPDATE_ORG_UNIT',
          `Updated OrgUnit: ${formData.name}`,
          updatedOu.name,
          'org_unit',
          formData.name
        );
        
        toast.success('Org Unit updated successfully');
      } else {
        await api.post<OrgUnit>('/api/org-units/', {
          ...formData,
          parentId: formData.parentId || null,
          type: formData.type || null
        });
        if (currentPage === 1) {
          await fetchOrgUnits();
        } else {
          setCurrentPage(1);
        }
        await fetchAllOrgUnits();
        toast.success('Org Unit created successfully');
      }
      setIsModalOpen(false);
    } catch (error: any) {
      toast.error(error.message || 'Failed to save org unit');
    }
  };

  // Helper to resolve parent name
  const getParentName = (parentId: string | null) => {
    if (!parentId) return 'None (Root)';
    const parent = allOrgUnits.find(ou => ou.id === parentId);
    return parent ? parent.name : 'Unknown';
  };

  // Option items avoiding the currently edited OrgUnit as parent
  const parentOptions = allOrgUnits.filter(ou => !isEditMode || ou.id !== editId);

  if (!isAdmin) {
    return <div className="p-8 text-center text-red-500">Access Denied. Admins Only.</div>;
  }

  return (
    <div className="w-full">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-900">
            <Network className="h-8 w-8 text-[#0A4D27]" />
            Organization Units
          </h1>
          <p className="text-gray-500 mt-1">Manage Colleges, Departments, Offices, and Units.</p>
        </div>
        <Button 
          onClick={handleOpenAdd}
          className="bg-[#0A4D27] hover:bg-[#083E1D] text-white gap-2 h-11 px-6 rounded-xl shadow-sm"
        >
          <Plus className="h-4 w-4" />
          Add Org Unit
        </Button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto bg-card rounded-md border-0 sm:border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[30%] pl-6">Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Hierarchy (Parent)</TableHead>
                <TableHead className="text-right pr-6">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                     <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-[#0A4D27]" />
                     Loading structure...
                  </TableCell>
                </TableRow>
              ) : orgUnits.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                    No Organization Units found.
                  </TableCell>
                </TableRow>
              ) : (
                orgUnits.map((ou) => (
                  <TableRow key={ou.id}>
                    <TableCell className="pl-6 font-medium flex items-center gap-2">
                      <FolderTree className="h-4 w-4 text-muted-foreground ml-2" />
                      {ou.name}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{ou.type || 'Unit'}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {getParentName(ou.parentId)}
                    </TableCell>
                    <TableCell className="text-right pr-6 gap-2 flex justify-end">
                      <Button variant="ghost" size="sm" onClick={() => handleOpenEdit(ou)}>
                        <Edit className="h-4 w-4 text-muted-foreground hover:text-blue-600" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setOuToDelete(ou)}>
                        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-red-500" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
        <PaginationControls
          count={orgUnitCount}
          currentPage={currentPage}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={handlePageSizeChange}
          disabled={isLoading}
        />
      </div>

      {/* Add/Edit Modal Overlay */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">{isEditMode ? 'Edit Organization Unit' : 'Add New Organization Unit'}</h2>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="space-y-2">
                <label htmlFor="org-unit-name" className="text-sm font-medium text-gray-700">Name</label>
                <Input 
                  id="org-unit-name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  className="h-11 rounded-xl"
                  placeholder="e.g. College of Engineering"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="org-unit-type" className="text-sm font-medium text-gray-700">Type</label>
                <select 
                  id="org-unit-type"
                  name="type"
                  value={formData.type}
                  onChange={handleInputChange}
                  className="flex h-11 w-full items-center justify-between rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                >
                  <option value="College">College</option>
                  <option value="Department">Department</option>
                  <option value="Office">Office</option>
                  <option value="Unit">Unit</option>
                </select>
              </div>

              <div className="space-y-2">
                <label htmlFor="org-unit-parent" className="text-sm font-medium text-gray-700">Parent (Optional)</label>
                <select 
                  id="org-unit-parent"
                  name="parentId"
                  value={formData.parentId}
                  onChange={handleInputChange}
                  className="flex h-11 w-full items-center justify-between rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                >
                  <option value="">None (Top-level)</option>
                  {parentOptions.map(ou => (
                    <option key={ou.id} value={ou.id}>{ou.name}</option>
                  ))}
                </select>
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setIsModalOpen(false)}
                  className="h-11 rounded-xl px-6"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="h-11 rounded-xl px-6 bg-[#0A4D27] hover:bg-[#083E1D] text-white"
                >
                  {isEditMode ? 'Save Changes' : 'Create'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Alert */}
      <AlertDialog open={!!ouToDelete} onOpenChange={(open) => !open && !isDeleting && setOuToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Organization Unit</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the Org Unit <strong>{ouToDelete?.name}</strong>?
              This action cannot be undone. You can only delete org units that have no users, folders, documents, or sub-units.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={(e) => { e.preventDefault(); handleDelete(); }}
              disabled={isDeleting}
              className="bg-red-600 text-white hover:bg-red-700 hover:text-white focus:ring-red-600"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
