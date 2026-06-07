import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_BRAND_YELLOW, CHART_REMAINING } from "@/lib/chart-colors";
import { formatStorageMbWithGb, formatStoragePercent } from "@/lib/storage";
import { HardDrive } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { StorageChartTooltip } from "@/components/dashboard/StorageChartTooltip";

export type StorageStats = {
  org_unit_name?: string;
  used_mb: number;
  quota_mb: number;
  org_units_quota_mb?: number | null;
  org_units_allocation_remaining_mb?: number | null;
  remaining_mb: number;
  percent_used: number;
};

type StorageUtilizationChartProps = {
  storage: StorageStats | null;
  isGlobal?: boolean;
};

export function StorageUtilizationChart({ storage, isGlobal = false }: StorageUtilizationChartProps) {
  if (!storage) {
    return null;
  }

  const chartData = [
    { name: "Used Storage", value: storage.used_mb, color: CHART_BRAND_YELLOW },
    { name: "Remaining Storage", value: storage.remaining_mb, color: CHART_REMAINING },
  ];
  const percentLabel = formatStoragePercent(storage.percent_used, storage.used_mb);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-sm font-medium">Storage Utilization</CardTitle>
          {storage.org_unit_name && (
            <p className="text-xs text-muted-foreground mt-1">{storage.org_unit_name}</p>
          )}
        </div>
        <HardDrive className="h-4 w-4 text-[#00491E]" />
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-[180px_1fr] items-center">
          <div className="flex flex-col items-center">
            <div className="relative h-[180px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={52}
                    outerRadius={72}
                    paddingAngle={2}
                    minAngle={storage.used_mb > 0 ? 4 : 0}
                    stroke="none"
                  >
                    {chartData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<StorageChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <div className="text-xl font-bold text-gray-900">{percentLabel}</div>
                {storage.used_mb > 0 ? (
                  <div className="text-xs font-medium text-gray-600 mt-0.5">
                    {storage.used_mb.toFixed(2)} MB
                  </div>
                ) : (
                  <div className="text-xs font-medium text-gray-600">Used</div>
                )}
              </div>
            </div>
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-2">
              {chartData.map((entry) => (
                <div key={entry.name} className="flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full border border-gray-300"
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="text-xs font-medium text-gray-700">{entry.name}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-4">
              <span className="font-medium text-gray-700">Used Storage</span>
              <span className="font-semibold text-gray-900 text-right">{formatStorageMbWithGb(storage.used_mb)}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="font-medium text-gray-700">Remaining Storage (files)</span>
              <span className="font-semibold text-gray-900 text-right">{formatStorageMbWithGb(storage.remaining_mb)}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="font-medium text-gray-700">
                {isGlobal ? "System Storage Limit" : "Quota"}
              </span>
              <span className="font-semibold text-gray-900 text-right">{formatStorageMbWithGb(storage.quota_mb)}</span>
            </div>
            {isGlobal && storage.org_units_quota_mb != null ? (
              <div className="flex items-center justify-between gap-4">
                <span className="font-medium text-gray-700">Total Top-Level Allocated</span>
                <span className="font-semibold text-gray-900 text-right">
                  {formatStorageMbWithGb(storage.org_units_quota_mb)}
                </span>
              </div>
            ) : null}
            {isGlobal && storage.org_units_allocation_remaining_mb != null ? (
              <div className="flex items-center justify-between gap-4">
                <span className="font-medium text-gray-700">System Allocation Remaining</span>
                <span className="font-semibold text-gray-900 text-right">
                  {formatStorageMbWithGb(storage.org_units_allocation_remaining_mb)}
                </span>
              </div>
            ) : null}
            <div className="flex items-center justify-between gap-4">
              <span className="font-medium text-gray-700">Percentage Used</span>
              <span className="font-semibold text-gray-900">{percentLabel}</span>
            </div>
            {isGlobal ? (
              <p className="text-xs text-muted-foreground pt-1">
                Remaining Storage (files) is based on uploaded documents. System Allocation Remaining
                is the unassigned top-level quota pool. Child units receive storage from their parent
                envelope and are not counted in top-level allocation totals.
              </p>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
