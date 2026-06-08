import React, { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { fetchSystemSettings, updateSystemSettings } from "@/lib/system-settings";
import { formatStorageMbWithGb } from "@/lib/storage";
import {
  getPresetForQuotaMb,
  getQuotaMbForPreset,
  formatStorageQuotaMb,
  MAX_SYSTEM_STORAGE_QUOTA_MB,
  SYSTEM_STORAGE_QUOTA_PRESETS,
  type SystemStorageQuotaPreset,
} from "@/lib/storage-quota-presets";

function extractStorageQuotaError(error: unknown): string | null {
  if (!error || typeof error !== "object") return null;
  const err = error as { errors?: Record<string, unknown> };
  const errors = err.errors;
  if (!errors || typeof errors !== "object") return null;
  const field = errors.storage_quota_mb ?? errors.storageQuotaMb;
  if (Array.isArray(field) && field[0]) return String(field[0]);
  if (typeof field === "string") return field;
  return null;
}

export function SystemSettingsForm() {
  const [uploadLimitMb, setUploadLimitMb] = useState("15");
  const [storageQuotaMb, setStorageQuotaMb] = useState("5120");
  const [storageQuotaPreset, setStorageQuotaPreset] = useState<SystemStorageQuotaPreset>("5120");
  const [storageUsedMb, setStorageUsedMb] = useState(0);
  const [allocatedStorageMb, setAllocatedStorageMb] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const minQuotaMb = useMemo(
    () => Math.max(Math.ceil(storageUsedMb), allocatedStorageMb),
    [storageUsedMb, allocatedStorageMb]
  );

  const selectedQuotaMb = Number(storageQuotaMb);
  const quotaTooLow =
    Number.isFinite(selectedQuotaMb) && selectedQuotaMb > 0 && selectedQuotaMb < minQuotaMb;

  useEffect(() => {
    fetchSystemSettings()
      .then((settings) => {
        setUploadLimitMb(String(settings.uploadLimitMb));
        const quotaMb = String(settings.storageQuotaMb);
        setStorageQuotaMb(quotaMb);
        setStorageQuotaPreset(
          getPresetForQuotaMb(settings.storageQuotaMb, SYSTEM_STORAGE_QUOTA_PRESETS, "5120")
        );
        setStorageUsedMb(settings.storageUsedMb ?? 0);
        setAllocatedStorageMb(settings.allocatedStorageMb ?? 0);
      })
      .catch(() => toast.error("Failed to load system settings."))
      .finally(() => setLoading(false));
  }, []);

  const handleQuotaPresetChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const preset = event.target.value as SystemStorageQuotaPreset;
    setStorageQuotaPreset(preset);
    setStorageQuotaMb(getQuotaMbForPreset(preset, SYSTEM_STORAGE_QUOTA_PRESETS, storageQuotaMb));
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    const uploadValue = Number(uploadLimitMb);
    const quotaValue = Number(storageQuotaMb);
    if (!Number.isFinite(uploadValue) || uploadValue < 1 || uploadValue > 500) {
      toast.error("Upload limit must be between 1 and 500 MB.");
      return;
    }
    if (!Number.isFinite(quotaValue) || quotaValue < 1) {
      toast.error("Storage quota must be at least 1 MB.");
      return;
    }
    if (quotaValue > MAX_SYSTEM_STORAGE_QUOTA_MB) {
      toast.error(
        `Storage quota cannot exceed ${formatStorageQuotaMb(MAX_SYSTEM_STORAGE_QUOTA_MB)}.`
      );
      return;
    }
    if (quotaValue < minQuotaMb) {
      toast.error(
        `Storage quota cannot be set below ${formatStorageMbWithGb(minQuotaMb)} (current file usage or top-level allocations).`
      );
      return;
    }

    setSaving(true);
    try {
      const updated = await updateSystemSettings({
        uploadLimitMb: uploadValue,
        storageQuotaMb: quotaValue,
      });
      setStorageUsedMb(updated.storageUsedMb ?? 0);
      setAllocatedStorageMb(updated.allocatedStorageMb ?? 0);
      toast.success("System settings updated.");
    } catch (error) {
      const fieldError = extractStorageQuotaError(error);
      toast.error(
        fieldError ?? (error instanceof Error ? error.message : "Failed to update system settings.")
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading system settings...
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="max-w-lg space-y-6">
      <div className="space-y-2">
        <Label htmlFor="upload-limit-mb">Maximum Upload Size (MB)</Label>
        <Input
          id="upload-limit-mb"
          type="number"
          min={1}
          max={500}
          value={uploadLimitMb}
          onChange={(event) => setUploadLimitMb(event.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Applies to document uploads. Default is 15 MB.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="system-storage-quota-preset">System Storage Quota</Label>
        <select
          id="system-storage-quota-preset"
          name="systemStorageQuotaPreset"
          title="System Storage Quota"
          value={storageQuotaPreset}
          onChange={handleQuotaPresetChange}
          className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          {SYSTEM_STORAGE_QUOTA_PRESETS.map((preset) => (
            <option key={preset.value} value={preset.value}>
              {preset.label}
            </option>
          ))}
        </select>
        {storageQuotaPreset === "custom" && (
          <div className="space-y-1">
            <Label htmlFor="system-storage-quota-mb">Custom Quota (MB)</Label>
            <Input
              id="system-storage-quota-mb"
              type="number"
              min={minQuotaMb > 0 ? minQuotaMb : 1}
              max={MAX_SYSTEM_STORAGE_QUOTA_MB}
              value={storageQuotaMb}
              onChange={(event) => setStorageQuotaMb(event.target.value)}
              required
              placeholder="Enter quota in MB"
            />
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          Overall storage limit for the entire system (all Office Units combined). Used for
          notification thresholds and upload blocking. Office Unit quotas are configured
          separately under Office Units.
          {storageQuotaPreset !== "custom" && (
            <>
              {" "}
              Selected: <span className="font-medium">{storageQuotaMb} MB</span>.
            </>
          )}
        </p>
        <div className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2 text-xs text-muted-foreground space-y-1">
          <p>
            Current file usage:{" "}
            <span className="font-medium text-gray-800">{formatStorageMbWithGb(storageUsedMb)}</span>
          </p>
          <p>
            Top-level allocated:{" "}
            <span className="font-medium text-gray-800">
              {formatStorageMbWithGb(allocatedStorageMb)}
            </span>
          </p>
          <p>
            Minimum allowed quota:{" "}
            <span className="font-medium text-gray-800">{formatStorageMbWithGb(minQuotaMb)}</span>
          </p>
        </div>
        {quotaTooLow ? (
          <p className="text-xs font-medium text-destructive">
            Selected quota is below the minimum allowed ({formatStorageMbWithGb(minQuotaMb)}).
            Reduce Office Unit quotas or choose a higher value.
          </p>
        ) : null}
      </div>

      <Button type="submit" disabled={saving || quotaTooLow}>
        {saving ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Saving...
          </>
        ) : (
          "Save System Settings"
        )}
      </Button>
    </form>
  );
}
