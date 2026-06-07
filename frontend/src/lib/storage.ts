import { formatStorageQuotaDual } from "@/lib/storage-quota-presets";

/** Format storage for display: GB primary with MB secondary (matches Office Units page). */
export function formatStorageMbWithGb(mb: number): string {
  const dual = formatStorageQuotaDual(Math.round(mb * 100) / 100);
  return dual.secondary ? `${dual.primary} (${dual.secondary})` : dual.primary;
}

/** Format storage usage percentage with adaptive precision for low usage. */
export function formatStoragePercent(percent: number, usedMb?: number): string {
  const roundedOne = Math.round(percent * 10) / 10;
  if (usedMb != null && usedMb > 0 && roundedOne === 0) {
    return "< 0.1%";
  }
  if (percent < 1) {
    const formatted = percent.toFixed(3).replace(/\.?0+$/, "");
    return `${formatted}%`;
  }
  return `${percent.toFixed(1)}%`;
}
