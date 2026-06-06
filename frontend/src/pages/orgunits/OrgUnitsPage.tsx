/**
 * OrgUnitsPage — organization unit and org type management (Admin only).
 *
 * APIs: /api/org-units/, /api/org-types/ (CRUD, soft delete OrgUnit).
 */
import React, { useState, useEffect, useMemo } from 'react';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { Network, Plus, Trash2, Edit, Loader2, FolderTree } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/auth-context';
import { PaginationControls } from '@/components/PaginationControls';
import { PaginatedResponse } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import type { OrgType, OrgUnit } from '@/types';
import {
  getPresetForQuotaMb,
  getQuotaMbForPreset,
  formatStorageQuotaMb,
  orgUnitQuotaExceedsSystemLimit,
  ORG_UNIT_STORAGE_QUOTA_PRESETS,
  type OrgUnitStorageQuotaPreset,
} from '@/lib/storage-quota-presets';
import { fetchSystemSettings } from '@/lib/system-settings';
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

const STORAGE_QUOTA_PRESETS = ORG_UNIT_STORAGE_QUOTA_PRESETS;

type StorageQuotaPreset = OrgUnitStorageQuotaPreset;

const resolvePresetForQuotaMb = (quotaMb: number | string | undefined): StorageQuotaPreset =>
  getPresetForQuotaMb(quotaMb, STORAGE_QUOTA_PRESETS, '1024');

export default function OrgUnitsPage() {
  const [orgUnits, setOrgUnits] = useState<OrgUnit[]>([]);
  const [allOrgUnits, setAllOrgUnits] = useState<OrgUnit[]>([]);
  const [orgTypes, setOrgTypes] = useState<OrgType[]>([]);
  const [orgUnitCount, setOrgUnitCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(true);
  const [isTypeLoading, setIsTypeLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isTypeModalOpen, setIsTypeModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    parentId: '',
    orgTypeId: '',
    storageQuotaMb: '1024',
    storageQuotaPreset: '1024' as StorageQuotaPreset,
  });
  const [typeFormData, setTypeFormData] = useState({ name: '', is_active: true });
  const [editingTypeId, setEditingTypeId] = useState<string | null>(null);
  const [ouToDelete, setOuToDelete] = useState<OrgUnit | null>(null);
  const [typeToDelete, setTypeToDelete] = useState<OrgType | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSavingType, setIsSavingType] = useState(false);
  const [systemStorageQuotaMb, setSystemStorageQuotaMb] = useState<number | null>(null);

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

  const fetchOrgTypes = async () => {
    try {
      setIsTypeLoading(true);
      const data = await api.get<OrgType[] | PaginatedResponse<OrgType>>('/api/org-types/', { includeInactive: 'true' });
      const results = Array.isArray(data) ? data : data.results;
      setOrgTypes([...results].sort((a, b) => a.name.localeCompare(b.name)));
    } catch (error: any) {
      toast.error(error.message || 'Failed to fetch org types');
    } finally {
      setIsTypeLoading(false);
    }
  };

  useEffect(() => {
    fetchOrgUnits();
  }, [currentPage, pageSize]);

  useEffect(() => {
    fetchAllOrgUnits();
    fetchOrgTypes();
    fetchSystemSettings()
      .then((settings) => setSystemStorageQuotaMb(settings.storageQuotaMb))
      .catch(() => setSystemStorageQuotaMb(null));
  }, []);

  useEffect(() => {
    if (!isModalOpen) return;
    fetchSystemSettings()
      .then((settings) => setSystemStorageQuotaMb(settings.storageQuotaMb))
      .catch(() => setSystemStorageQuotaMb(null));
  }, [isModalOpen]);

  const selectedOrgUnitQuotaMb = Number(formData.storageQuotaMb);
  const quotaExceedsSystemLimit = useMemo(() => {
    if (systemStorageQuotaMb == null) return false;
    if (!Number.isFinite(selectedOrgUnitQuotaMb) || selectedOrgUnitQuotaMb < 1) return false;
    return orgUnitQuotaExceedsSystemLimit(selectedOrgUnitQuotaMb, systemStorageQuotaMb);
  }, [formData.storageQuotaMb, selectedOrgUnitQuotaMb, systemStorageQuotaMb]);

  const systemQuotaLabel =
    systemStorageQuotaMb != null ? formatStorageQuotaMb(systemStorageQuotaMb) : null;

  useEffect(() => {
    const firstActiveType = orgTypes.find(type => type.is_active);
    if (isModalOpen && !formData.orgTypeId && firstActiveType) {
      setFormData(prev => ({ ...prev, orgTypeId: firstActiveType.id }));
    }
  }, [isModalOpen, formData.orgTypeId, orgTypes]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setCurrentPage(1);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleQuotaPresetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const preset = e.target.value as StorageQuotaPreset;

    setFormData((prev) => ({
      ...prev,
      storageQuotaPreset: preset,
      storageQuotaMb: getQuotaMbForPreset(preset, STORAGE_QUOTA_PRESETS, prev.storageQuotaMb),
    }));
  };

  const handleTypeInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setTypeFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleOpenAdd = () => {
    setFormData({
      name: '',
      parentId: '',
      orgTypeId: orgTypes.find(type => type.is_active)?.id || '',
      storageQuotaMb: '1024',
      storageQuotaPreset: '1024',
    });
    setIsEditMode(false);
    setEditId(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (ou: OrgUnit) => {
    const quotaMb = String(ou.storageQuotaMb || 1024);
    setFormData({
      name: ou.name,
      parentId: ou.parentId || '',
      orgTypeId: getOrgTypeId(ou),
      storageQuotaMb: quotaMb,
      storageQuotaPreset: resolvePresetForQuotaMb(quotaMb),
    });
    setIsEditMode(true);
    setEditId(ou.id);
    setIsModalOpen(true);
  };

  const resetTypeForm = () => {
    setTypeFormData({ name: '', is_active: true });
    setEditingTypeId(null);
  };

  const handleOpenTypeManager = () => {
    resetTypeForm();
    setIsTypeModalOpen(true);
  };

  const handleEditType = (type: OrgType) => {
    setEditingTypeId(type.id);
    setTypeFormData({ name: type.name, is_active: type.is_active });
  };

  const handleDelete = async () => {
    if (!ouToDelete) return;
    setIsDeleting(true);
    try {
      await api.delete(`/api/org-units/${ouToDelete.id}/`);
      await fetchOrgUnits();
      await fetchAllOrgUnits();
      toast.success('Office Unit deleted successfully');
      setOuToDelete(null);
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete org unit');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (quotaExceedsSystemLimit) {
      toast.error(
        systemQuotaLabel
          ? `Office Unit quota cannot exceed the system-wide limit (${systemQuotaLabel}).`
          : 'Office Unit quota cannot exceed the system-wide storage limit.'
      );
      return;
    }
    try {
      if (isEditMode && editId) {
        await api.put<OrgUnit>(`/api/org-units/${editId}/`, {
          name: formData.name,
          parentId: formData.parentId || null,
          org_type_id: formData.orgTypeId || null,
          storageQuotaMb: Number(formData.storageQuotaMb),
        });
        await fetchOrgUnits();
        await fetchAllOrgUnits();
        toast.success('Office Unit updated successfully');
      } else {
        await api.post<OrgUnit>('/api/org-units/', {
          name: formData.name,
          parentId: formData.parentId || null,
          org_type_id: formData.orgTypeId || null,
          storageQuotaMb: Number(formData.storageQuotaMb),
        });
        if (currentPage === 1) {
          await fetchOrgUnits();
        } else {
          setCurrentPage(1);
        }
        await fetchAllOrgUnits();
        toast.success('Office Unit created successfully');
      }
      setIsModalOpen(false);
    } catch (error: any) {
      toast.error(error.message || 'Failed to save org unit');
    }
  };

  const handleTypeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingType(true);
    const payload = {
      name: typeFormData.name,
      is_active: typeFormData.is_active,
    };

    try {
      const savedType = editingTypeId
        ? await api.put<OrgType>(`/api/org-types/${editingTypeId}/`, payload)
        : await api.post<OrgType>('/api/org-types/', payload);

      toast.success(editingTypeId ? 'Org Type updated successfully' : 'Org Type added successfully');
      resetTypeForm();
      await fetchOrgTypes();
      if (savedType.is_active) {
        setFormData(prev => ({ ...prev, orgTypeId: savedType.id }));
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to save org type');
    } finally {
      setIsSavingType(false);
    }
  };

  const handleDeleteType = async () => {
    if (!typeToDelete) return;
    setIsDeleting(true);
    try {
      await api.delete(`/api/org-types/${typeToDelete.id}/`);
      await fetchOrgTypes();
      toast.success('Org Type deleted successfully');
      setTypeToDelete(null);
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete org type');
    } finally {
      setIsDeleting(false);
    }
  };

  const getParentName = (parentId: string | null) => {
    if (!parentId) return 'None (Root)';
    const parent = allOrgUnits.find(ou => ou.id === parentId);
    return parent ? parent.name : 'Unknown';
  };

  const getOrgTypeId = (orgUnit: OrgUnit) => {
    const directId = orgUnit.orgTypeId || (orgUnit.org_type_id ? String(orgUnit.org_type_id) : '');
    if (directId) return directId;
    return orgTypes.find(type => type.name === orgUnit.type)?.id || '';
  };

  const getOrgTypeName = (orgUnit: OrgUnit) => {
    return orgUnit.orgTypeName || orgUnit.org_type_name || orgUnit.type || 'Unassigned';
  };

  const canDeleteOrgUnit = (orgUnit: OrgUnit) => orgUnit.canDelete !== false;
  const getDeleteBlockReason = (orgUnit: OrgUnit) => (
    orgUnit.deleteBlockReason || 'Cannot delete while this Office Unit contains users, folders, documents, or sub-units.'
  );

  const activeOrgTypes = orgTypes.filter(type => type.is_active);

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
            Office Units
          </h1>
          <p className="text-gray-500 mt-1">Manage office structure, storage quotas, and database-driven types.</p>
        </div>
        <Button
          onClick={handleOpenAdd}
          className="bg-[#0A4D27] hover:bg-[#083E1D] text-white gap-2 h-11 px-6 rounded-xl shadow-sm"
        >
          <Plus className="h-4 w-4" />
          Add Office Unit
        </Button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto bg-card rounded-md border-0 sm:border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[30%] pl-6">Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Storage</TableHead>
                <TableHead>Hierarchy (Parent)</TableHead>
                <TableHead className="text-right pr-6">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-[#0A4D27]" />
                    Loading structure...
                  </TableCell>
                </TableRow>
              ) : orgUnits.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                    No Office Units found.
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
                      <Badge variant="outline">{getOrgTypeName(ou)}</Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {(ou.storageUsedMb ?? 0).toString()} / {ou.storageQuotaMb ?? 1024} MB
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {getParentName(ou.parentId)}
                    </TableCell>
                    <TableCell className="text-right pr-6 gap-2 flex justify-end">
                      <Button variant="ghost" size="sm" onClick={() => handleOpenEdit(ou)}>
                        <Edit className="h-4 w-4 text-muted-foreground hover:text-blue-600" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => canDeleteOrgUnit(ou) ? setOuToDelete(ou) : toast.info(getDeleteBlockReason(ou))}
                        disabled={!canDeleteOrgUnit(ou)}
                        title={!canDeleteOrgUnit(ou) ? getDeleteBlockReason(ou) : 'Delete Office Unit'}
                        className="disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <Trash2 className={`h-4 w-4 ${canDeleteOrgUnit(ou) ? 'text-muted-foreground hover:text-red-500' : 'text-muted-foreground'}`} />
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

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">{isEditMode ? 'Edit Office Unit' : 'Add New Office Unit'}</h2>
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
                <div className="flex items-center justify-between gap-3">
                  <label htmlFor="org-unit-type" className="text-sm font-medium text-gray-700">Type</label>
                  <button
                    type="button"
                    onClick={handleOpenTypeManager}
                    className="text-sm font-medium text-[#0A4D27] hover:underline"
                  >
                    Add Type
                  </button>
                </div>
                <select
                  id="org-unit-type"
                  name="orgTypeId"
                  value={formData.orgTypeId}
                  onChange={handleInputChange}
                  required
                  disabled={isTypeLoading || activeOrgTypes.length === 0}
                  className="flex h-11 w-full items-center justify-between rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                >
                  <option value="">{isTypeLoading ? 'Loading types...' : 'Select Org Type'}</option>
                  {activeOrgTypes.map(type => (
                    <option key={type.id} value={type.id}>{type.name}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label htmlFor="org-unit-storage-quota-preset" className="text-sm font-medium text-gray-700">Storage Quota</label>
                <select
                  id="org-unit-storage-quota-preset"
                  name="storageQuotaPreset"
                  value={formData.storageQuotaPreset}
                  onChange={handleQuotaPresetChange}
                  className="flex h-11 w-full items-center justify-between rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  {STORAGE_QUOTA_PRESETS.map((preset) => (
                    <option key={preset.value} value={preset.value}>
                      {preset.label}
                    </option>
                  ))}
                </select>
                {formData.storageQuotaPreset === 'custom' && (
                  <div className="space-y-1">
                    <label htmlFor="org-unit-storage-quota" className="text-sm font-medium text-gray-700">Custom Quota (MB)</label>
                    <Input
                      id="org-unit-storage-quota"
                      name="storageQuotaMb"
                      type="number"
                      min={1}
                      value={formData.storageQuotaMb}
                      onChange={handleInputChange}
                      required
                      className="h-11 rounded-xl"
                      placeholder="Enter quota in MB"
                    />
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  Admin-only setting. Uploads are blocked when this Office Unit exceeds its quota.
                  System-wide storage limits are configured under Settings → System.
                  {systemQuotaLabel ? (
                    <> Current system limit: <span className="font-medium">{systemQuotaLabel}</span>.</>
                  ) : null}
                  {formData.storageQuotaPreset !== 'custom' && (
                    <> Selected: <span className="font-medium">{formData.storageQuotaMb} MB</span>.</>
                  )}
                </p>
                {quotaExceedsSystemLimit && systemQuotaLabel ? (
                  <p className="text-xs font-medium text-destructive">
                    Office Unit quota cannot exceed the system-wide limit ({systemQuotaLabel}). Lower the
                    quota or increase the system limit under Settings → System.
                  </p>
                ) : null}
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
                  disabled={!formData.orgTypeId || isTypeLoading || quotaExceedsSystemLimit}
                  className="h-11 rounded-xl px-6 bg-[#0A4D27] hover:bg-[#083E1D] text-white"
                >
                  {isEditMode ? 'Save Changes' : 'Create'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isTypeModalOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-7 py-6 border-b border-gray-100">
              <h2 className="text-xl font-bold leading-tight text-gray-900">Organization Types</h2>
              <p className="text-sm text-muted-foreground mt-1">Add or disable simple type names used by Office Units.</p>
            </div>

            <div className="px-7 py-6 space-y-6">
              <form onSubmit={handleTypeSubmit} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
                  <div className="space-y-2">
                    <label htmlFor="org-type-name" className="text-sm font-medium text-gray-700">Type Name</label>
                    <Input
                      id="org-type-name"
                      name="name"
                      value={typeFormData.name}
                      onChange={handleTypeInputChange}
                      required
                      className="h-11 rounded-xl"
                      placeholder="e.g. Institute"
                    />
                  </div>

                  <label className="flex h-11 items-center gap-2 text-sm text-gray-700">
                    <input
                      name="is_active"
                      type="checkbox"
                      checked={typeFormData.is_active}
                      onChange={handleTypeInputChange}
                      className="h-4 w-4 accent-[#0A4D27]"
                    />
                    Active
                  </label>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button
                    type="submit"
                    disabled={isSavingType}
                    className="h-11 rounded-xl px-5 bg-[#0A4D27] hover:bg-[#083E1D] text-white sm:min-w-[120px]"
                  >
                    {isSavingType ? 'Saving...' : editingTypeId ? 'Save Type' : 'Add Type'}
                  </Button>
                  {editingTypeId && (
                    <Button type="button" variant="outline" onClick={resetTypeForm} className="h-11 rounded-xl px-5 sm:min-w-[120px]">
                      Cancel Edit
                    </Button>
                  )}
                </div>
              </form>

              <div className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-[#526B57]">Existing Types</h3>
                <div className="border rounded-xl overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {isTypeLoading ? (
                        <TableRow>
                          <TableCell colSpan={3} className="h-20 text-center text-muted-foreground">
                            <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2 text-[#0A4D27]" />
                            Loading types...
                          </TableCell>
                        </TableRow>
                      ) : orgTypes.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={3} className="h-20 text-center text-muted-foreground">
                            No Org Types found.
                          </TableCell>
                        </TableRow>
                      ) : (
                        orgTypes.map(type => (
                          <TableRow key={type.id}>
                            <TableCell className="font-medium">{type.name}</TableCell>
                            <TableCell>
                              <Badge variant={type.is_active ? 'outline' : 'secondary'}>
                                {type.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              <Button type="button" variant="ghost" size="sm" onClick={() => handleEditType(type)}>
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button type="button" variant="ghost" size="sm" onClick={() => setTypeToDelete(type)}>
                                <Trash2 className="h-4 w-4 text-red-500" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </div>

            <div className="px-7 py-4 border-t border-gray-100 flex justify-end">
              <Button type="button" variant="outline" onClick={() => setIsTypeModalOpen(false)} className="h-11 rounded-xl px-6">
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      <AlertDialog open={!!ouToDelete} onOpenChange={(open) => !open && !isDeleting && setOuToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Office Unit</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the Office Unit <strong>{ouToDelete?.name}</strong>?
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
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={!!typeToDelete} onOpenChange={(open) => !open && !isDeleting && setTypeToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Organization Type</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the Org Type <strong>{typeToDelete?.name}</strong>?
              This only works if no Office Units are using it. If it is already used, edit it and uncheck Active instead.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => { e.preventDefault(); handleDeleteType(); }}
              disabled={isDeleting}
              className="bg-red-600 text-white hover:bg-red-700 hover:text-white focus:ring-red-600"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
