import { api } from "@/lib/api";
import type { AppNotification, SystemSettings } from "@/types";

function mapSystemSettings(raw: Record<string, unknown>): SystemSettings {
  return {
    uploadLimitMb: Number(raw.upload_limit_mb ?? 15),
    storageQuotaMb: Number(raw.storage_quota_mb ?? 500),
    storageQuotaExceeded: Boolean(raw.storage_quota_exceeded),
    storageUsedMb: raw.storage_used_mb != null ? Number(raw.storage_used_mb) : undefined,
    storageRemainingMb: raw.storage_remaining_mb != null ? Number(raw.storage_remaining_mb) : undefined,
    storageUsagePercentage:
      raw.storage_usage_percentage != null ? Number(raw.storage_usage_percentage) : undefined,
    allocatedStorageMb:
      raw.allocated_storage_mb != null ? Number(raw.allocated_storage_mb) : undefined,
    allocationRemainingMb:
      raw.allocation_remaining_mb != null ? Number(raw.allocation_remaining_mb) : undefined,
    allocationPercentage:
      raw.allocation_percentage != null ? Number(raw.allocation_percentage) : undefined,
    updatedAt: typeof raw.updated_at === "string" ? raw.updated_at : undefined,
  };
}

function mapNotification(raw: Record<string, unknown>): AppNotification {
  return {
    id: Number(raw.id),
    title: String(raw.title ?? ""),
    message: String(raw.message ?? ""),
    level: (raw.level as AppNotification["level"]) ?? "warning",
    thresholdPercent: raw.threshold_percent != null ? Number(raw.threshold_percent) : null,
    audience: (raw.audience as AppNotification["audience"]) ?? "all",
    createdAt: String(raw.created_at ?? ""),
  };
}

export async function fetchSystemSettings(): Promise<SystemSettings> {
  const data = await api.get<Record<string, unknown>>("/api/system/settings/");
  return mapSystemSettings(data);
}

export async function updateSystemSettings(payload: {
  uploadLimitMb?: number;
  storageQuotaMb?: number;
}): Promise<SystemSettings> {
  const data = await api.patch<Record<string, unknown>>("/api/system/settings/", {
    ...(payload.uploadLimitMb != null ? { upload_limit_mb: payload.uploadLimitMb } : {}),
    ...(payload.storageQuotaMb != null ? { storage_quota_mb: payload.storageQuotaMb } : {}),
  });
  return mapSystemSettings(data);
}

export async function fetchNotifications(): Promise<AppNotification[]> {
  const data = await api.get<Record<string, unknown>[]>("/api/notifications/");
  return (data ?? []).map(mapNotification);
}

export async function fetchNotificationCount(): Promise<number> {
  const data = await api.get<{ count: number }>("/api/notifications/unread-count/");
  return Number(data?.count ?? 0);
}

export function formatUploadSizeError(limitMb: number): string {
  return `File exceeds the maximum allowed size of ${limitMb} MB. Please compress the file and try again.`;
}
