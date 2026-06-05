import { formatStorageMbWithGb } from "@/lib/storage";

type TooltipPayload = {
  name?: string;
  value?: number;
  payload?: { color?: string };
};

type StorageChartTooltipProps = {
  active?: boolean;
  payload?: TooltipPayload[];
};

/** Recharts tooltip with readable contrast on light card backgrounds. */
export function StorageChartTooltip({ active, payload }: StorageChartTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }

  const entry = payload[0];
  const label = entry.name ?? "Storage";
  const value = formatStorageMbWithGb(Number(entry.value ?? 0));

  return (
    <div className="rounded-lg border border-gray-300 bg-white px-3 py-2 shadow-md">
      <p className="text-sm font-semibold text-gray-900">{label}</p>
      <p className="text-sm font-medium text-gray-800">{value}</p>
    </div>
  );
}
