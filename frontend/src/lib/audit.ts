import { api } from "./api";

export type AuditAction = 
  | "LOGIN" 
  | "LOGOUT" 
  | "UPLOAD" 
  | "SCAN"
  | "DOWNLOAD"
  | "DOWNLOAD_DOCUMENT"
  | "EXPORT_AUDIT_CSV"
  | "EXPORT_AUDIT_XLSX"
  | "CREATE_FOLDER" 
  | "DELETE_FOLDER" 
  | "ARCHIVE_DOCUMENT"
  | "UNARCHIVE_DOCUMENT"
  | "DELETE_DOCUMENT"
  | "RESTORE_DOCUMENT"
  | "RESTORE"
  | "PERMANENT_DELETE"
  | "CREATE_USER"
  | "UPDATE_USER"
  | "DELETE_USER"
  | "ACTIVATE_USER"
  | "DEACTIVATE_USER"
  | "RESET_PASSWORD"
  | "PASSWORD_RESET_REQUEST"
  | "PASSWORD_RESET_SUCCESS"
  | "RENAME_FOLDER"
  | "RENAME_DOCUMENT"
  | "UPDATE_ORG_UNIT"
  | "UPDATE_CATEGORY"
  | "DELETE_CATEGORY";

export async function logAudit(
  action: AuditAction, 
  details: string, 
  targetOrgUnitName?: string,
  targetType?: string,
  targetName?: string
) {
  try {
    const userJson = localStorage.getItem("auth_user");
    const user = userJson ? JSON.parse(userJson) : null;
    
    await api.post("/api/audit-logs/", {
      userId: user?.id || "system",
      userEmail: user?.email || "system",
      action,
      details,
      targetOrgUnitName,
      targetType,
      targetName,
      ipAddress: "127.0.0.1"
    });
  } catch (error) {
    console.error("Failed to log audit:", error);
  }
}
