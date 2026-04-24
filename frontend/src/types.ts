export type UserRole = 'admin' | 'staff' | 'dept_head';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  departmentId?: string;
  orgUnitId?: string;
  orgUnitName?: string;
  isActive?: boolean;
}

export interface Department {
  id: string;
  name: string;
}

export type DocumentCategory = 'Memo' | 'Approved Documents' | 'Reports' | 'Letters' | 'Forms' | 'Others';

export type DocumentStatus = 'Received';

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
  createdAt: string;
}

export interface Document {
  id: string;
  title: string;
  file_name?: string;
  filePath: string;
  folderId: string;
  categoryId: string;
  category?: string;
  uploaderId: string;
  code?: string;
  requestor?: string;
  description?: string;
  keywords?: string[];
  filingYear: number;
  status: DocumentStatus;
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
}

export interface AuditLog {
  id: string;
  userId: string;
  action: string;
  details: string;
  ipAddress: string;
  createdAt: string;
}
