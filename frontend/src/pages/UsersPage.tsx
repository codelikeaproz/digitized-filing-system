import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
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
  MoreVertical
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
import { logAudit } from '@/lib/audit';

type User = {
  id: string;
  fullName: string;
  email: string;
  role: string;
  isActive: boolean;
  createdAt: string;
  orgUnitId?: string;
  orgUnitName?: string;
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'dept_head' | 'staff'>('all');
  const [orgUnitFilter, setOrgUnitFilter] = useState<string>('all');
  
  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  
  // Form State
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [orgUnits, setOrgUnits] = useState<{id: string, name: string}[]>([]);
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    role: 'staff',
    orgUnitId: '',
    password: '',
    isActive: true
  });
  
  const { user: currentUser } = useAuth();

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const data = await api.get<User[]>('/api/users');
      setUsers(data);
    } catch (error: any) {
      toast.error(error.message || 'Failed to fetch users');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchOrgUnits = async () => {
    try {
      const data = await api.get<{id: string, name: string}[]>('/api/org-units');
      setOrgUnits(data);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchOrgUnits();
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }));
  };

  const handleOpenAdd = () => {
    setFormData({ fullName: '', email: '', role: 'staff', orgUnitId: orgUnits[0]?.id || '', password: '', isActive: true });
    setIsAddModalOpen(true);
  };

  const handleOpenEdit = (user: User) => {
    setSelectedUser(user);
    setFormData({ 
      fullName: user.fullName, 
      email: user.email, 
      role: user.role, 
      // @ts-ignore
      orgUnitId: user.orgUnitId || '',
      password: '', // blank intentionally
      isActive: user.isActive 
    });
    setIsEditModalOpen(true);
  };

  const handleOpenDelete = (user: User) => {
    setSelectedUser(user);
    setIsDeleteModalOpen(true);
  };

  const handleSubmitAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = { ...formData };
      if (payload.role === 'admin') payload.orgUnitId = '';

      const newUser = await api.post<User>('/api/users', payload);
      setUsers([...users, newUser]);
      
      const roleDisplay = payload.role === 'admin' ? 'Admin' : (payload.role === 'dept_head' ? 'Dept Head' : 'Staff');
      const targetOrg = orgUnits.find(o => o.id === newUser.orgUnitId);
      
      await logAudit(
        'CREATE_USER', 
        `Created user: ${newUser.email} as ${roleDisplay}${targetOrg ? ` under ${targetOrg.name}` : ''}`,
        targetOrg?.name,
        'user',
        newUser.email
      );

      toast.success('User created successfully');
      setIsAddModalOpen(false);
    } catch (error: any) {
      toast.error(error.message || 'Failed to create user');
    }
  };

  const handleSubmitEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    try {
      // Omit password if blank
      const payload = { ...formData } as any;
      if (!payload.password) delete payload.password;
      if (payload.role === 'admin') payload.orgUnitId = '';
      
      const updatedUser = await api.put<User>(`/api/users/${selectedUser.id}`, payload);
      setUsers(users.map(u => u.id === updatedUser.id ? updatedUser : u));
      
      const roleDisplay = payload.role === 'admin' ? 'Admin' : (payload.role === 'dept_head' ? 'Dept Head' : 'Staff');
      const targetOrg = orgUnits.find(o => o.id === updatedUser.orgUnitId);
      let details = `Updated user: ${updatedUser.email}`;
      if (selectedUser.role !== updatedUser.role) {
        const oldRole = selectedUser.role === 'admin' ? 'Admin' : (selectedUser.role === 'dept_head' ? 'Dept Head' : 'Staff');
        details += ` role from ${oldRole} to ${roleDisplay}`;
      } else {
        details += ` settings`;
      }

      await logAudit(
        'UPDATE_USER', 
        details,
        targetOrg?.name,
        'user',
        updatedUser.email
      );

      toast.success('User updated successfully');
      setIsEditModalOpen(false);
    } catch (error: any) {
      toast.error(error.message || 'Failed to update user');
    }
  };

  const handleToggleStatus = async (user: User) => {
    if (user.id === currentUser?.id) {
      toast.error('You cannot deactivate your own account.');
      return;
    }
    
    try {
      await api.patch(`/api/users/${user.id}/status`, { isActive: !user.isActive });
      setUsers(users.map(u => u.id === user.id ? { ...u, isActive: !user.isActive } : u));
      
      const action = !user.isActive ? 'ACTIVATE_USER' : 'DEACTIVATE_USER';
      const targetOrg = orgUnits.find(o => o.id === user.orgUnitId);
      await logAudit(
        action,
        `${!user.isActive ? 'Activated' : 'Deactivated'} user: ${user.email}`,
        targetOrg?.name,
        'user',
        user.email
      );

      toast.success(`User ${!user.isActive ? 'activated' : 'deactivated'} successfully`);
    } catch (error: any) {
      toast.error(error.message || 'Failed to update user status');
    }
  };

  const handleDelete = async () => {
    if (!selectedUser) return;
    try {
      await api.delete(`/api/users/${selectedUser.id}`);
      setUsers(users.filter(u => u.id !== selectedUser.id));
      
      const targetOrg = orgUnits.find(o => o.id === selectedUser.orgUnitId);
      await logAudit(
        'DELETE_USER',
        `Deleted user: ${selectedUser.email}`,
        targetOrg?.name,
        'user',
        selectedUser.email
      );

      toast.success('User deleted successfully');
      setIsDeleteModalOpen(false);
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete user');
    }
  };

  const filteredUsers = users.filter(u => {
    const matchesSearch = u.fullName.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          u.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter === 'all' || u.role.toLowerCase() === roleFilter;
    const matchesOrgUnit = orgUnitFilter === 'all' || u.orgUnitId === orgUnitFilter;

    return matchesSearch && matchesRole && matchesOrgUnit;
  });

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
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value as 'all' | 'admin' | 'dept_head' | 'staff')}
              className="h-10 px-3 py-2 rounded-xl border border-gray-200 text-sm font-medium focus:ring-2 focus:ring-[#0A4D27] outline-none"
            >
              <option value="all">All Roles</option>
              <option value="admin">Admin Only</option>
              <option value="dept_head">Dept Head Only</option>
              <option value="staff">Staff Only</option>
            </select>
            <select
              value={orgUnitFilter}
              onChange={(e) => setOrgUnitFilter(e.target.value)}
              className="h-10 px-3 py-2 rounded-xl border border-gray-200 text-sm font-medium focus:ring-2 focus:ring-[#0A4D27] outline-none max-w-[200px]"
            >
              <option value="all">All Org Units</option>
              {orgUnits.map(ou => (
                <option key={ou.id} value={ou.id}>{ou.name}</option>
              ))}
            </select>
          </div>
          <div className="text-sm font-medium text-gray-500">
            {filteredUsers.length} Users Total
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
                <TableHead>Org Unit</TableHead>
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
              ) : filteredUsers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    No users found matching your search.
                  </TableCell>
                </TableRow>
              ) : (
                filteredUsers.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="pl-6 font-medium">
                      {user.fullName}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{user.email}</TableCell>
                    <TableCell>
                      {user.role === 'admin' ? (
                        <Badge variant="secondary" className="bg-purple-100 text-purple-700 hover:bg-purple-100 border-purple-200">
                          <ShieldAlert className="mr-1 h-3 w-3" /> Admin
                        </Badge>
                      ) : user.role === 'dept_head' ? (
                        <Badge variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100 border-amber-200">
                          <ShieldCheck className="mr-1 h-3 w-3" /> Dept Head
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
                      ) : (
                        <Badge variant="secondary" className="bg-gray-100 text-gray-600 hover:bg-gray-100 border-gray-200">
                          <XCircle className="mr-1 h-3 w-3" /> Inactive
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                      {new Date(user.createdAt).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </TableCell>
                    <TableCell className="text-right pr-6">
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
                            onClick={() => handleToggleStatus(user)}
                            disabled={user.id === currentUser?.id}
                          >
                            <span className="flex items-center">
                              {user.isActive ? (
                                <>
                                  <XCircle className="mr-2 h-4 w-4 text-orange-500" /> Deactivate 
                                </>
                              ) : (
                                <>
                                  <CheckCircle2 className="mr-2 h-4 w-4 text-green-500" /> Activate
                                </>
                              )}
                            </span>
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleOpenEdit(user)}>
                            <Edit className="mr-2 h-4 w-4 text-blue-500" /> Edit
                          </DropdownMenuItem>
                          {user.id !== currentUser?.id && <DropdownMenuSeparator />}
                          <DropdownMenuItem 
                            className="text-destructive focus:bg-destructive/10"
                            onClick={() => handleOpenDelete(user)}
                            disabled={user.id === currentUser?.id}
                          >
                            <Trash2 className="mr-2 h-4 w-4" /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
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
                <label className="text-sm font-medium text-gray-700">Full Name</label>
                <Input 
                  name="fullName"
                  value={formData.fullName}
                  onChange={handleInputChange}
                  required
                  className="h-11 rounded-xl"
                  placeholder="John Doe"
                />
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
                  name="role"
                  value={formData.role}
                  onChange={handleInputChange}
                  className="flex h-11 w-full items-center justify-between rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="staff">Staff</option>
                  <option value="dept_head">Department Head</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Organization Unit</label>
                {formData.role === 'admin' ? (
                  <div className="flex h-11 w-full items-center rounded-xl border border-input bg-muted px-3 py-2 text-sm text-muted-foreground">
                    Global Access (Not applicable for Admins)
                  </div>
                ) : (
                  <select 
                    name="orgUnitId"
                    value={formData.orgUnitId}
                    onChange={handleInputChange}
                    required
                    className="flex h-11 w-full items-center justify-between rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  >
                    <option value="">Select Organization Unit</option>
                    {orgUnits.map(ou => (
                      <option key={ou.id} value={ou.id}>{ou.name}</option>
                    ))}
                  </select>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Password {isEditModalOpen && <span className="text-gray-400 font-normal">(Leave blank to keep unchanged)</span>}
                </label>
                <Input 
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  required={isAddModalOpen}
                  className="h-11 rounded-xl"
                  placeholder="••••••••"
                />
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
