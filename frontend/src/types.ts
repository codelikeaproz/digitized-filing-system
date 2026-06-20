export type UserRole = 'admin' | 'staff' | 'dept_head';

export interface User {
  id: string;
  email: string;
  fullName: string;
  employeeNumber?: string;
  firstName?: string;
  lastName?: string;
  suffix?: string;
  role: UserRole;
  departmentId?: string;
  orgUnitId?: string;
  orgUnitName?: string;
  profilePictureUrl?: string | null;
  isActive?: boolean;
}

export interface Department {
  id: string;
  name: string;
}

export interface OrgType {
  id: string;
  name: string;
  code: string | null;
  is_active: boolean;
  sort_order: number;
}

export interface OrgUnitAllocationContext {
  source: 'system' | 'parent';
  parentName: string | null;
  parentAllocationMb: number;
  childrenAllocatedMb: number;
  availableForAllocationMb: number;
}

export interface OrgUnit {
  id: string;
  name: string;
  parentId: string | null;
  parentName?: string | null;
  type?: string | null;
  org_type_id?: string | number | null;
  org_type_name?: string | null;
  orgTypeId?: string | null;
  orgTypeName?: string | null;
  createdAt: string;
  userCount?: number;
  folderCount?: number;
  documentCount?: number;
  childCount?: number;
  canDelete?: boolean;
  deleteBlockReason?: string;
  storageQuotaMb?: number;
  storageUsedMb?: number;
  storageUsedDisplayMb?: number;
  storageRemainingMb?: number;
  storagePercentUsed?: number;
  childrenAllocatedMb?: number;
  availableForAllocationMb?: number;
  storageOwnUsedMb?: number;
  allocationContext?: OrgUnitAllocationContext;
}

export interface DocumentRequisitioner {
  employeeId?: string | null;
  source?: "directory" | "manual";
  employeeNumber: string;
  firstName: string;
  lastName: string;
  suffix?: string;
  fullName: string;
}

export interface Folder {
  id: string;
  name: string;
  parentId: string | null;
  departmentId?: string | null;
  orgUnitId?: string | null;
  createdBy: string;
  createdAt: string;
}

export interface Category {
  id: string;
  name: string;
  org_unit?: number | string | null;
  orgUnitId?: string | null;
  createdAt?: string;
  document_count?: number;
  documentCount?: number;
  inUse?: boolean;
}

export interface Document {
  id: string;
  title: string;
  file_name?: string;
  filePath: string;
  folderId: string;
  categoryId: string;
  category?: string;
  code?: string;
  uploaderId: string;
  requestor?: string;
  requisitioners?: DocumentRequisitioner[];
  description?: string;
  keywords?: string[];
  filingYear: number;
  source: 'Scanned' | 'Uploaded';
  mimeType: string;
  isDeleted: boolean;
  deletedAt?: any;
  deletedBy?: string;
  createdAt: any;
  created_at?: string;
  mime_type?: string;
  file_size?: number;
  file_url?: string;
  googleDriveLink?: string;
}

export interface EmployeeDirectoryEntry {
  id: string;
  employeeNumber: string;
  firstName: string;
  lastName: string;
  suffix?: string;
  fullName: string;
  isActive?: boolean;
  createdAt?: string;
  referencedDocumentCount?: number;
  scopedReferencedDocumentCount?: number;
  canDelete?: boolean;
  deleteBlockReason?: string;
  canChangeEmployeeNumber?: boolean;
  employeeNumberBlockReason?: string;
}

export interface RequisitionerTaggedDocument {
  id: string;
  title: string;
  code?: string | null;
  category: string;
  orgUnit: string;
  uploadedAt: string;
  owner?: string;
  keywords?: string[];
}

export interface RequisitionerDocumentsResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: RequisitionerTaggedDocument[];
  totalTaggedDocuments: number;
}

export interface AuditLog {
  id: string;
  userId: string;
  action: string;
  details: string;
  ipAddress: string;
  createdAt: string;
}

export interface SystemSettings {
  uploadLimitMb: number;
  storageQuotaMb: number;
  storageQuotaExceeded?: boolean;
  storageUsedMb?: number;
  storageRemainingMb?: number;
  storageUsagePercentage?: number;
  allocatedStorageMb?: number;
  allocationRemainingMb?: number;
  allocationPercentage?: number;
  updatedAt?: string;
}

export interface AppNotification {
  id: number;
  title: string;
  message: string;
  level: 'warning' | 'alert' | 'critical' | 'exceeded';
  thresholdPercent: number | null;
  audience: 'all' | 'admin';
  createdAt: string;
}
