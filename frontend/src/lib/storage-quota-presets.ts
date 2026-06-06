export type StorageQuotaPresetOption = {
  value: string;
  label: string;
  mb: number | null;
};

export const SYSTEM_STORAGE_QUOTA_PRESETS = [
  { value: "5120", label: "5 GB", mb: 5120 },
  { value: "15360", label: "15 GB", mb: 15360 },
  { value: "102400", label: "100 GB", mb: 102400 },
  { value: "512000", label: "500 GB", mb: 512000 },
  { value: "1048576", label: "1 TB", mb: 1048576 },
  { value: "custom", label: "Custom", mb: null },
] as const satisfies readonly StorageQuotaPresetOption[];

export type SystemStorageQuotaPreset = (typeof SYSTEM_STORAGE_QUOTA_PRESETS)[number]["value"];

export const ORG_UNIT_STORAGE_QUOTA_PRESETS = [
  { value: "500", label: "500 MB", mb: 500 },
  { value: "1024", label: "1 GB", mb: 1024 },
  { value: "5120", label: "5 GB", mb: 5120 },
  { value: "15360", label: "15 GB", mb: 15360 },
  { value: "30720", label: "30 GB", mb: 30720 },
  { value: "51200", label: "50 GB", mb: 51200 },
  { value: "102400", label: "100 GB", mb: 102400 },
  { value: "512000", label: "500 GB", mb: 512000 },
  { value: "1048576", label: "1 TB", mb: 1048576 },
  { value: "custom", label: "Custom", mb: null },
] as const satisfies readonly StorageQuotaPresetOption[];

export type OrgUnitStorageQuotaPreset = (typeof ORG_UNIT_STORAGE_QUOTA_PRESETS)[number]["value"];

export function getPresetForQuotaMb<T extends string>(
  quotaMb: number | string | undefined,
  presets: readonly StorageQuotaPresetOption[],
  fallback: T
): T {
  const numericQuota = Number(quotaMb);
  if (!Number.isFinite(numericQuota) || numericQuota <= 0) {
    return fallback;
  }
  const matchedPreset = presets.find((preset) => preset.mb === numericQuota);
  return (matchedPreset ? matchedPreset.value : "custom") as T;
}

export function getQuotaMbForPreset(
  presetValue: string,
  presets: readonly StorageQuotaPresetOption[],
  currentMb: string
): string {
  const matchedPreset = presets.find((option) => option.value === presetValue);
  return matchedPreset?.mb != null ? String(matchedPreset.mb) : currentMb;
}

/** Maximum system storage quota accepted by the API (1 TB). */
export const MAX_SYSTEM_STORAGE_QUOTA_MB = 1048576;

const QUOTA_LABEL_PRESETS = [...ORG_UNIT_STORAGE_QUOTA_PRESETS, ...SYSTEM_STORAGE_QUOTA_PRESETS];

export function formatStorageQuotaMb(mb: number): string {
  const matched = QUOTA_LABEL_PRESETS.find((preset) => preset.mb === mb);
  return matched?.label ?? `${mb} MB`;
}

export function orgUnitQuotaExceedsSystemLimit(orgUnitQuotaMb: number, systemQuotaMb: number): boolean {
  return Number.isFinite(orgUnitQuotaMb) && Number.isFinite(systemQuotaMb) && orgUnitQuotaMb > systemQuotaMb;
}
