/**
 * UsersPage — user account management (Admin and Dept Head).
 *
 * Admin: manage all users. Dept Head: Staff only within assigned OrgUnit.
 * APIs: GET/POST /api/users, PUT/PATCH/DELETE /api/users/{id},
 *       activate/deactivate, resend-activation.
 */
import React, { useState, useEffect } from 'react';
import { api, PaginatedResponse } from '@/lib/api';
import { toast } from 'sonner';
import { 
  Users, 
  Trash2, 
  Edit, 
  UserPlus, 
  Search, 
  Loader2,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  MoreVertical,
  Mail,
  ClockAlert
} from 'lucide-react';
import { Button, buttonVariants } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/auth-context';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { PaginationControls } from '@/components/PaginationControls';
import { formatManilaDate } from '@/lib/time';
import { RolePermissionLegend } from '@/components/users/RolePermissionLegend';
import { sanitizeEmployeeNumberInput, validateEmployeeNumber } from '@/lib/employee-number';

const SUFFIX_OPTIONS = [
  { value: '', label: 'No Suffix' },
  { value: 'Jr.', label: 'Jr.' },
  { value: 'Sr.', label: 'Sr.' },
  { value: 'I', label: 'I' },
  { value: 'II', label: 'II' },
  { value: 'III', label: 'III' },
  { value: 'IV', label: 'IV' },
  { value: 'V', label: 'V' },
] as const;

type User = {
  id: string;
  fullName: string;
  employeeNumber?: string;
  firstName?: string;
  lastName?: string;
  suffix?: string;
  email: string;
  role: string;
  isActive: boolean;
  createdAt: string;
  orgUnitId?: string;
  orgUnitName?: string;
  isLastActiveAdmin?: boolean;
  hasUsablePassword?: boolean;
  activationStatus?: 'active' | 'pending' | 'expired' | 'inactive';
  activationEmailSentAt?: string | null;
  activationExpiresAt?: string | null;
  canManage?: boolean;
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'dept_head' | 'staff'>('all');
  const [orgUnitFilter, setOrgUnitFilter] = useState<string>('all');
  const [userCount, setUserCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  
  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  
  // Form State
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [statusTargetUser, setStatusTargetUser] = useState<User | null>(null);
  const [orgUnits, setOrgUnits] = useState<{id: string, name: string}[]>([]);
  const [formData, setFormData] = useState({
    employeeNumber: '',
    firstName: '',
    lastName: '',
    suffix: '',
    email: '',
    role: 'staff',
    orgUnitId: '',
    password: '',
    isActive: true
  });
  const [employeeNumberError, setEmployeeNumberError] = useState('');
  
  const { user: currentUser } = useAuth();
  const currentUserRole = currentUser?.role?.toLowerCase();
  const isAdmin = currentUserRole === 'admin';
  const isDeptHead = currentUserRole === 'dept_head';
  const currentUserOrgUnitId = currentUser?.orgUnitId ? String(currentUser.orgUnitId) : '';
  const isSelectedLastActiveAdmin = Boolean(selectedUser?.isLastActiveAdmin);
  const lastAdminMessage = 'At least one active Admin must remain in the system.';

  const suffixOptions = React.useMemo(() => {
    const options: { value: string; label: string }[] = SUFFIX_OPTIONS.map((option) => ({
      value: option.value,
      label: option.label,
    }));
    const current = formData.suffix;
    if (current && !options.some((option) => option.value === current)) {
      options.push({ value: current, label: current });
    }
    return options;
  }, [formData.suffix]);

  const canManageUser = (target: User) => {
    if (typeof target.canManage === 'boolean') return target.canManage;
    if (isAdmin) return true;
    return isDeptHead && target.role === 'staff' && String(target.orgUnitId || '') === currentUserOrgUnitId;
  };

  const isReadOnlyHeadRow = (target: User) => isDeptHead && target.role === 'dept_head' && !canManageUser(target);

  const isPendingActivation = (target: User) => (
    target.activationStatus ? target.activationStatus === 'pending' : !target.isActive && target.hasUsablePassword === false
  );
  const isActivationExpired = (target: User) => target.activationStatus === 'expired';

  const canDeleteUser = (target: User) => {
    return isAdmin && target.id !== currentUser?.id && !target.isLastActiveAdmin;
  };

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const params: Record<string, string | number> = {
        page: currentPage,
        page_size: pageSize,
      };
      if (debouncedSearch) params.search = debouncedSearch;
      if (isDeptHead) {
        params.role = 'staff';
        if (currentUserOrgUnitId) params.orgUnitId = currentUserOrgUnitId;
      } else {
        if (roleFilter !== 'all') params.role = roleFilter;
        if (orgUnitFilter !== 'all') params.orgUnitId = orgUnitFilter;
      }

      const data = await api.get<PaginatedResponse<User>>('/api/users', params);
      setUsers(data.results);
      setUserCount(data.count);
    } catch (error: any) {
      toast.error(error.message || 'Failed to fetch users');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchOrgUnits = async () => {
    try {
      if (isDeptHead && currentUserOrgUnitId) {
        setOrgUnits([{ id: currentUserOrgUnitId, name: currentUser?.orgUnitName || 'Assigned Office Unit' }]);
        return;
      }
      const data = await api.get<PaginatedResponse<{id: string, name: string}>>('/api/org-units/', { page_size: 100 });
      setOrgUnits(data.results);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [currentPage, pageSize, debouncedSearch, roleFilter, orgUnitFilter, currentUserRole, currentUserOrgUnitId]);

  useEffect(() => {
    fetchOrgUnits();
  }, [currentUserRole, currentUserOrgUnitId]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setCurrentPage(1);
  };

  const handleRoleFilterChange = (value: 'all' | 'admin' | 'dept_head' | 'staff') => {
    setRoleFilter(value);
    setCurrentPage(1);
  };

  const handleOrgUnitFilterChange = (value: string) => {
    setOrgUnitFilter(value);
    setCurrentPage(1);
  };

  const applyApiFieldErrors = (errors: unknown) => {
    if (!errors || typeof errors !== 'object') return;
    const record = errors as Record<string, unknown>;
    const employeeError = record.employeeNumber;
    if (Array.isArray(employeeError) && employeeError.length) {
      setEmployeeNumberError(String(employeeError[0]));
    } else if (typeof employeeError === 'string') {
      setEmployeeNumberError(employeeError);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const nextValue =
      name === 'employeeNumber'
        ? sanitizeEmployeeNumberInput(value)
        : type === 'checkbox'
          ? (e.target as HTMLInputElement).checked
          : value;

    if (name === 'employeeNumber') {
      setEmployeeNumberError('');
    }

    setFormData(prev => ({
      ...prev,
      [name]: nextValue
    }));
  };

  const handleOpenAdd = () => {
    setEmployeeNumberError('');
    setFormData({
      employeeNumber: '',
      firstName: '',
      lastName: '',
      suffix: '',
      email: '',
      role: 'staff',
      orgUnitId: isDeptHead ? currentUserOrgUnitId : orgUnits[0]?.id || '',
      password: '',
      isActive: true
    });
    setIsAddModalOpen(true);
  };

  const handleOpenEdit = (user: User) => {
    if (!canManageUser(user)) {
      toast.error('You can only manage staff within your organization.');
      return;
    }
    setSelectedUser(user);
    setEmployeeNumberError('');
    setFormData({
      employeeNumber: user.employeeNumber || '',
      firstName: user.firstName || user.fullName.split(' ')[0] || '',
      lastName: user.lastName || user.fullName.split(' ').slice(1).join(' ') || '',
      suffix: user.suffix || '',
      email: user.email,
      role: isDeptHead ? 'staff' : user.role,
      orgUnitId: isDeptHead ? currentUserOrgUnitId : user.orgUnitId || '',
      password: '',
      isActive: user.isActive
    });
    setIsEditModalOpen(true);
  };

  const handleOpenDelete = (user: User) => {
    if (!canDeleteUser(user)) {
      toast.error(user.isLastActiveAdmin ? lastAdminMessage : 'Only Admin users can delete user accounts.');
      return;
    }
    if (user.isLastActiveAdmin) {
      toast.error(lastAdminMessage);
      return;
    }
    setSelectedUser(user);
    setIsDeleteModalOpen(true);
  };

  const handleSubmitAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const employeeValidationError = validateEmployeeNumber(formData.employeeNumber);
    if (employeeValidationError) {
      setEmployeeNumberError(employeeValidationError);
      toast.error(employeeValidationError);
      return;
    }
    try {
      const payload = {
        employeeNumber: formData.employeeNumber.trim(),
        firstName: formData.firstName,
        lastName: formData.lastName,
        suffix: formData.suffix,
        email: formData.email,
        role: isDeptHead ? 'staff' : formData.role,
        orgUnitId: isDeptHead ? currentUserOrgUnitId : formData.role === 'admin' ? null : formData.orgUnitId,
      };

      const newUser = await api.post<User>('/api/users', payload);
      if (currentPage === 1) {
        await fetchUsers();
      } else {
        setCurrentPage(1);
      }
      
      toast.success('User created successfully');
      toast.info('Activation email sent. The user must set their own password before login.');
      setIsAddModalOpen(false);
    } catch (error: any) {
      applyApiFieldErrors(error.errors);
      toast.error(error.message || 'Failed to create user');
    }
  };

  const handleSubmitEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    const employeeValidationError = validateEmployeeNumber(formData.employeeNumber);
    if (employeeValidationError) {
      setEmployeeNumberError(employeeValidationError);
      toast.error(employeeValidationError);
      return;
    }
    if (selectedUser.isLastActiveAdmin && formData.role !== 'admin') {
      toast.error(lastAdminMessage);
      return;
    }
    try {
      // Omit password if blank
      const payload = {
        ...formData,
        role: isDeptHead ? 'staff' : formData.role,
        orgUnitId: isDeptHead ? currentUserOrgUnitId : formData.role === 'admin' ? null : formData.orgUnitId,
      } as any;
      if (!payload.password) delete payload.password;
      
      const updatedUser = await api.put<User>(`/api/users/${selectedUser.id}`, payload);
      await fetchUsers();

      toast.success('User updated successfully');
      setIsEditModalOpen(false);
    } catch (error: any) {
      applyApiFieldErrors(error.errors);
      toast.error(error.message || 'Failed to update user');
    }
  };

  const handleOpenStatusModal = (user: User) => {
    if (user.id === currentUser?.id) {
      toast.error('You cannot deactivate your own account.');
      return;
    }
    if (user.isLastActiveAdmin && user.isActive) {
      toast.error(lastAdminMessage);
      return;
    }
    if (isPendingActivation(user) || isActivationExpired(user)) {
      toast.error('This account is pending activation. The user must set their password from the email link.');
      return;
    }
    if (!canManageUser(user)) {
      toast.error('You can only manage staff within your organization.');
      return;
    }

    setStatusTargetUser(user);
    setIsStatusModalOpen(true);
  };

  const handleConfirmStatusChange = async () => {
    if (!statusTargetUser) return;
    try {
      const action = statusTargetUser.isActive ? 'deactivate' : 'activate';
      await api.patch(`/api/users/${statusTargetUser.id}/${action}`);
      await fetchUsers();

      toast.success(`User ${!statusTargetUser.isActive ? 'activated' : 'deactivated'} successfully`);
      setIsStatusModalOpen(false);
      setStatusTargetUser(null);
    } catch (error: any) {
      toast.error(error.message || 'Failed to update user status');
    }
  };

  const handleResendActivation = async (user: User) => {
    if (!canManageUser(user)) {
      toast.error('You can only manage staff within your organization.');
      return;
    }
    if (!isPendingActivation(user) && !isActivationExpired(user)) {
      toast.error('Activation email can only be resent to pending or expired activation accounts.');
      return;
    }

    try {
      const response = await api.post<{ message: string }>(`/api/users/${user.id}/resend-activation`);
      toast.success(response.message || 'Activation email resent successfully.');
    } catch (error: any) {
      toast.error(error.message || 'Failed to resend activation email');
    }
  };

  const handleDelete = async () => {
    if (!selectedUser) return;
    if (selectedUser.isLastActiveAdmin) {
      toast.error(lastAdminMessage);
      setIsDeleteModalOpen(false);
      return;
    }
    try {
      await api.delete(`/api/users/${selectedUser.id}`);
      await fetchUsers();

      toast.success('User deleted successfully');
      setIsDeleteModalOpen(false);
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete user');
    }
  };

  return (
    <div className="w-full">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-900">
            <Users className="h-8 w-8 text-[#0A4D27]" />
            User Management
          </h1>
          <p className="text-gray-500 mt-1">Manage system administrators and staff accounts.</p>
        </div>
        <Button 
          onClick={handleOpenAdd}
          className="bg-[#0A4D27] hover:bg-[#083E1D] text-white gap-2 h-11 px-6 rounded-xl shadow-sm"
        >
          <UserPlus className="h-4 w-4" />
          Add User
        </Button>
      </div>

      <div className="mb-6">
        <RolePermissionLegend />
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b border-gray-100 flex flex-col sm:flex-row gap-4 items-center justify-between bg-gray-50/50">
          <div className="flex flex-col sm:flex-row gap-4 items-center flex-1">
            <div className="relative w-full sm:w-96">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input 
                placeholder="Search users by name or email..." 
                className="pl-9 h-10 w-full rounded-xl border-gray-200 focus:border-[#0A4D27] focus:ring-[#0A4D27]"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            {isAdmin ? (
              <>
                <select
                  title="Select role"
                  value={roleFilter}
                  onChange={(e) => handleRoleFilterChange(e.target.value as 'all' | 'admin' | 'dept_head' | 'staff')}
                  className="h-10 px-3 py-2 rounded-xl border border-gray-200 text-sm font-medium focus:ring-2 focus:ring-[#0A4D27] outline-none"
                >
                  <option value="all">All Roles</option>
                  <option value="admin">Admin Only</option>
                  <option value="dept_head">Head Only</option>
                  <option value="staff">Staff Only</option>
                </select>
                <select
                  title="Select org unit"
                  value={orgUnitFilter}
                  onChange={(e) => handleOrgUnitFilterChange(e.target.value)}
                  className="h-10 px-3 py-2 rounded-xl border border-gray-200 text-sm font-medium focus:ring-2 focus:ring-[#0A4D27] outline-none max-w-[200px]"
                >
                  <option value="all">All Office Units</option>
                  {orgUnits.map(ou => (
                    <option key={ou.id} value={ou.id}>{ou.name}</option>
                  ))}
                </select>
              </>
            ) : (
              <div className="h-10 px-3 py-2 rounded-xl border border-gray-200 bg-white text-sm text-gray-600">
                Office Unit: <span className="font-semibold text-gray-800">{currentUser?.orgUnitName || 'Assigned Office Unit'}</span>
              </div>
            )}
          </div>
          <div className="text-sm font-medium text-gray-500 text-right">
            <div>{userCount} Users Total</div>
            {isDeptHead && (
              <div className="text-xs font-normal text-gray-400 mt-0.5">
                Head accounts are read-only
              </div>
            )}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto bg-card rounded-md border-0 sm:border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[20%] pl-6">Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Office Unit</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date Joined</TableHead>
                <TableHead className="text-right pr-6">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-[#0A4D27]" />
                    Loading users...
                  </TableCell>
                </TableRow>
              ) : users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    {isDeptHead
                      ? 'No staff accounts found. Add staff to manage them here.'
                      : 'No users found matching your search.'}
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user) => (
                  <TableRow
                    key={user.id}
                    className={isReadOnlyHeadRow(user) ? 'bg-amber-50/40' : undefined}
                  >
                    <TableCell className="pl-6 font-medium">
                      <div>
                        {user.fullName}
                        {user.id === currentUser?.id && (
                          <span className="ml-1.5 text-xs font-normal text-muted-foreground">(You)</span>
                        )}
                      </div>
                      {user.employeeNumber && (
                        <div className="text-xs text-muted-foreground">#{user.employeeNumber}</div>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{user.email}</TableCell>
                    <TableCell>
                      {user.role === 'admin' ? (
                        <Badge variant="secondary" className="bg-purple-100 text-purple-700 hover:bg-purple-100 border-purple-200">
                          <ShieldAlert className="mr-1 h-3 w-3" /> Admin
                        </Badge>
                      ) : user.role === 'dept_head' ? (
                        <Badge variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100 border-amber-200">
                          <ShieldCheck className="mr-1 h-3 w-3" /> Head
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="bg-blue-100 text-blue-700 hover:bg-blue-100 border-blue-200">
                          <ShieldCheck className="mr-1 h-3 w-3" /> Staff
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.role === 'admin' ? (
                        <span className="text-muted-foreground text-sm">Global Access</span>
                      ) : (
                        <span className="text-foreground text-sm font-medium">{user.orgUnitName || 'Unknown'}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.isActive ? (
                        <Badge variant="secondary" className="bg-green-100 text-green-700 hover:bg-green-100 border-green-200">
                          <CheckCircle2 className="mr-1 h-3 w-3" /> Active
                        </Badge>
                      ) : isActivationExpired(user) ? (
                        <Badge
                          variant="secondary"
                          className="bg-red-100 text-red-700 hover:bg-red-100 border-red-200"
                          title={user.activationExpiresAt ? `Expired at ${user.activationExpiresAt}` : undefined}
                        >
                          <ClockAlert className="mr-1 h-3 w-3" /> Activation Expired
                        </Badge>
                      ) : isPendingActivation(user) ? (
                        <Badge variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100 border-amber-200">
                          <XCircle className="mr-1 h-3 w-3" /> Pending Activation
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="bg-gray-100 text-gray-600 hover:bg-gray-100 border-gray-200">
                          <XCircle className="mr-1 h-3 w-3" /> Inactive
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                      {formatManilaDate(user.createdAt)}
                    </TableCell>
                    <TableCell className="text-right pr-6">
                      {isReadOnlyHeadRow(user) ? (
                        <Badge variant="outline" className="text-muted-foreground font-normal">
                          Read-only
                        </Badge>
                      ) : (
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            className={cn(
                              buttonVariants({ variant: "ghost" }),
                              "h-8 w-8 p-0"
                            )}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem 
                              onClick={() => handleOpenStatusModal(user)}
                              disabled={!canManageUser(user) || isPendingActivation(user) || isActivationExpired(user) || user.id === currentUser?.id || Boolean(user.isLastActiveAdmin && user.isActive)}
                            >
                              <span className="flex items-center">
                                {user.isActive ? (
                                  <>
                                    <XCircle className="mr-2 h-4 w-4 text-orange-500" /> Deactivate Account
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle2 className="mr-2 h-4 w-4 text-green-500" /> Activate Account
                                  </>
                                )}
                              </span>
                            </DropdownMenuItem>
                            {(isPendingActivation(user) || isActivationExpired(user)) && (
                              <DropdownMenuItem onClick={() => handleResendActivation(user)} disabled={!canManageUser(user)}>
                                <Mail className="mr-2 h-4 w-4 text-emerald-600" /> Resend Activation Email
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem onClick={() => handleOpenEdit(user)} disabled={!canManageUser(user)}>
                              <Edit className="mr-2 h-4 w-4 text-blue-500" /> Edit
                            </DropdownMenuItem>
                            {isAdmin && user.id !== currentUser?.id && <DropdownMenuSeparator />}
                            {isAdmin && (
                              <DropdownMenuItem 
                                className="text-destructive focus:bg-destructive/10"
                                onClick={() => handleOpenDelete(user)}
                                disabled={!canDeleteUser(user)}
                              >
                                <Trash2 className="mr-2 h-4 w-4" /> Delete
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
        <PaginationControls
          count={userCount}
          currentPage={currentPage}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={handlePageSizeChange}
          disabled={isLoading}
        />
      </div>

      {/* Add / Edit Modal Overlay */}
      {(isAddModalOpen || isEditModalOpen) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">
                {isAddModalOpen ? 'Add New User' : 'Edit User'}
              </h2>
            </div>
            
            <form onSubmit={isAddModalOpen ? handleSubmitAdd : handleSubmitEdit} className="p-6 space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Employee Number</label>
                <Input
                  name="employeeNumber"
                  value={formData.employeeNumber}
                  onChange={handleInputChange}
                  className="h-11 rounded-xl"
                  placeholder="e.g. 20240001"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  required
                />
                <p className="text-xs text-muted-foreground">Digits only. Must be unique across all users.</p>
                {employeeNumberError && (
                  <p className="text-xs text-destructive">{employeeNumberError}</p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">First Name</label>
                  <Input
                    name="firstName"
                    value={formData.firstName}
                    onChange={handleInputChange}
                    required
                    className="h-11 rounded-xl"
                    placeholder="John"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">Last Name</label>
                  <Input
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleInputChange}
                    required
                    className="h-11 rounded-xl"
                    placeholder="Doe"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Suffix</label>
                <select
                  title="Select suffix"
                  name="suffix"
                  value={formData.suffix}
                  onChange={handleInputChange}
                  className="flex h-11 w-full items-center justify-between rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  {suffixOptions.map((option) => (
                    <option key={option.value || 'none'} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Email Address</label>
                <Input 
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  className="h-11 rounded-xl"
                  placeholder="john@example.com"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Role</label>
                <select 
                  title="Select role"
                  name="role"
                  value={formData.role}
                  onChange={handleInputChange}
                  disabled={isDeptHead || (isEditModalOpen && isSelectedLastActiveAdmin)}
                  className="flex h-11 w-full items-center justify-between rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="staff">Staff</option>
                  {isAdmin && <option value="dept_head">Head</option>}
                  {isAdmin && <option value="admin">Admin</option>}
                </select>
                {isDeptHead && (
                  <p className="text-xs text-gray-500">
                    Heads can create and edit Staff accounts only.
                  </p>
                )}
                {isEditModalOpen && isSelectedLastActiveAdmin && (
                  <p className="text-xs text-amber-700">
                    This role cannot be changed because at least one active Admin must remain.
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Office Unit</label>
                {formData.role === 'admin' ? (
                  <div className="flex h-11 w-full items-center rounded-xl border border-input bg-muted px-3 py-2 text-sm text-muted-foreground">
                    Global Access (Not applicable for Admins)
                  </div>
                ) : (
                  <select 
                    title="Select org unit"
                    name="orgUnitId"
                    value={formData.orgUnitId}
                    onChange={handleInputChange}
                    required
                    disabled={isDeptHead}
                    className="flex h-11 w-full items-center justify-between rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <option value="">Select Office Unit</option>
                    {orgUnits.map(ou => (
                      <option key={ou.id} value={ou.id}>{ou.name}</option>
                    ))}
                  </select>
                )}
                {isDeptHead && (
                  <p className="text-xs text-gray-500">
                    Office Unit is locked to your assigned scope.
                  </p>
                )}
              </div>

              <div className="rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                {isAddModalOpen
                  ? 'No default password will be created. The user will receive an activation email to set their own password.'
                  : 'Passwords are not edited here. Users must use account activation or password reset to set their password.'}
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => {
                    setIsAddModalOpen(false);
                    setIsEditModalOpen(false);
                  }}
                  className="h-11 rounded-xl px-6"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="h-11 rounded-xl px-6 bg-[#0A4D27] hover:bg-[#083E1D] text-white"
                >
                  {isAddModalOpen ? 'Create User' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Activate / Deactivate Confirmation Modal */}
      {isStatusModalOpen && statusTargetUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 text-center animate-in fade-in zoom-in-95 duration-200">
            <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
              {statusTargetUser.isActive ? (
                <XCircle className="h-6 w-6 text-amber-600" />
              ) : (
                <CheckCircle2 className="h-6 w-6 text-green-600" />
              )}
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">
              {statusTargetUser.isActive ? 'Deactivate Account?' : 'Activate Account?'}
            </h3>
            <p className="text-sm text-gray-500 mb-6">
              Are you sure you want to {statusTargetUser.isActive ? 'deactivate' : 'activate'}{' '}
              <span className="font-semibold text-gray-700">{statusTargetUser.fullName}</span>?
            </p>
            <div className="flex gap-3 justify-center">
              <Button
                variant="outline"
                onClick={() => {
                  setIsStatusModalOpen(false);
                  setStatusTargetUser(null);
                }}
                className="h-11 rounded-xl flex-1 border-gray-200 hover:bg-gray-50"
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirmStatusChange}
                className="h-11 rounded-xl flex-1 bg-[#0A4D27] hover:bg-[#083E1D] text-white"
              >
                Confirm
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 text-center animate-in fade-in zoom-in-95 duration-200">
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <ShieldAlert className="h-6 w-6 text-red-600" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Delete User?</h3>
            <p className="text-sm text-gray-500 mb-6">
              Are you sure you want to delete <span className="font-semibold text-gray-700">{selectedUser.fullName}</span>? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-center">
              <Button 
                variant="outline" 
                onClick={() => setIsDeleteModalOpen(false)}
                className="h-11 rounded-xl flex-1 border-gray-200 hover:bg-gray-50"
              >
                Cancel
              </Button>
              <Button 
                variant="destructive" 
                onClick={handleDelete}
                className="h-11 rounded-xl flex-1 bg-red-600 hover:bg-red-700 text-white"
              >
                Yes, Delete
              </Button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
