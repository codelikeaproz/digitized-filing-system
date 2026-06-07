import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_BRAND_GREEN, CHART_BRAND_YELLOW, CHART_REMAINING } from "@/lib/chart-colors";
import { formatStorageMbWithGb } from "@/lib/storage";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type OfficeUnitStorageRow = {
  org_unit_id: string;
  org_unit_name: string;
  quota_mb: number;
  used_mb: number;
  remaining_mb: number;
  usage_percentage: number;
  has_children?: boolean;
  children_allocated_mb?: number;
  available_for_allocation_mb?: number;
};

type OfficeUnitStorageComparisonChartProps = {
  data: OfficeUnitStorageRow[];
  totalUsedMb?: number;
  totalQuotaMb?: number | null;
};

type ChartRow = {
  name: string;
  used_mb: number;
  quota_mb: number;
  children_allocated_mb: number;
  available_for_allocation_mb: number;
  has_children: boolean;
  total_envelope_mb: number;
};

function buildChartData(data: OfficeUnitStorageRow[]): ChartRow[] {
  return data.map((row) => {
    const hasChildren = Boolean(row.has_children);
    const childrenAllocated = hasChildren ? Number(row.children_allocated_mb ?? 0) : 0;
    const availableForAllocation = hasChildren
      ? Number(row.available_for_allocation_mb ?? 0)
      : 0;

    return {
      name: row.org_unit_name,
      used_mb: row.used_mb,
      quota_mb: hasChildren ? 0 : row.quota_mb,
      children_allocated_mb: childrenAllocated,
      available_for_allocation_mb: availableForAllocation,
      has_children: hasChildren,
      total_envelope_mb: row.quota_mb,
    };
  });
}

function ComparisonTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ dataKey?: string; value?: number; payload?: ChartRow }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;

  const row = payload[0]?.payload;
  if (!row) return null;

  return (
    <div className="rounded-lg border bg-background px-3 py-2 text-xs shadow-md">
      <p className="font-semibold text-gray-900 mb-1.5">{label}</p>
      {row.has_children ? (
        <div className="space-y-1 text-muted-foreground">
          <p>
            <span className="font-medium text-gray-700">Total Envelope:</span>{" "}
            {formatStorageMbWithGb(row.total_envelope_mb)}
          </p>
          <p>
            <span className="font-medium text-gray-700">Allocated to Children:</span>{" "}
            {formatStorageMbWithGb(row.children_allocated_mb)}
          </p>
          <p>
            <span className="font-medium text-gray-700">Available for Allocation:</span>{" "}
            {formatStorageMbWithGb(row.available_for_allocation_mb)}
          </p>
          <p>
            <span className="font-medium text-gray-700">Used:</span>{" "}
            {formatStorageMbWithGb(row.used_mb)}
          </p>
        </div>
      ) : (
        <div className="space-y-1 text-muted-foreground">
          <p>
            <span className="font-medium text-gray-700">Quota:</span>{" "}
            {formatStorageMbWithGb(row.quota_mb)}
          </p>
          <p>
            <span className="font-medium text-gray-700">Used:</span>{" "}
            {formatStorageMbWithGb(row.used_mb)}
          </p>
        </div>
      )}
    </div>
  );
}

export function OfficeUnitStorageComparisonChart({
  data,
  totalUsedMb,
  totalQuotaMb,
}: OfficeUnitStorageComparisonChartProps) {
  const chartData = buildChartData(data);
  const hasParentUnits = chartData.some((row) => row.has_children);
  const hasTinyUsedBars = data.some(
    (row) => row.used_mb > 0 && row.quota_mb > 0 && row.used_mb / row.quota_mb < 0.01,
  );

  const resolvedTotalUsedMb =
    totalUsedMb ?? data.reduce((sum, row) => sum + row.used_mb, 0);
  const resolvedTotalQuotaMb =
    totalQuotaMb ?? data.reduce((sum, row) => sum + row.quota_mb, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Office Unit Storage Comparison</CardTitle>
        <p className="text-xs text-muted-foreground">
          Used vs allocated quota per Office Unit — identify high consumers and nearly full units.
          {hasParentUnits
            ? " Parent units show how their envelope is split between children and remaining pool."
            : null}
        </p>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">No Office Units to compare.</p>
        ) : (
          <>
            <div className="h-[320px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 48 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8E4" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    interval={0}
                    angle={-25}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis tick={{ fontSize: 11 }} unit=" MB" />
                  <Tooltip content={<ComparisonTooltip />} />
                  <Legend />
                  <Bar dataKey="used_mb" name="Used" fill={CHART_BRAND_YELLOW} radius={[4, 4, 0, 0]} />
                  {hasParentUnits ? (
                    <>
                      <Bar
                        dataKey="children_allocated_mb"
                        name="Allocated to Children"
                        stackId="parentQuota"
                        fill={CHART_BRAND_GREEN}
                        radius={[0, 0, 0, 0]}
                      />
                      <Bar
                        dataKey="available_for_allocation_mb"
                        name="Available for Allocation"
                        stackId="parentQuota"
                        fill={CHART_REMAINING}
                        radius={[4, 4, 0, 0]}
                      />
                    </>
                  ) : null}
                  <Bar dataKey="quota_mb" name="Quota" fill={CHART_BRAND_GREEN} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 space-y-2 border-t pt-4 text-sm">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center justify-between gap-4 sm:justify-start">
                  <span className="font-medium text-gray-700">Total Used (all units)</span>
                  <span className="font-semibold text-gray-900">
                    {formatStorageMbWithGb(resolvedTotalUsedMb)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4 sm:justify-start">
                  <span className="font-medium text-gray-700">Total Quota (top-level)</span>
                  <span className="font-semibold text-gray-900">
                    {formatStorageMbWithGb(resolvedTotalQuotaMb)}
                  </span>
                </div>
              </div>
              {totalQuotaMb != null ? (
                <p className="text-xs text-muted-foreground">
                  Total Quota reflects top-level Office Units only. Child quotas are drawn from their
                  parent envelope.
                </p>
              ) : null}
              {hasTinyUsedBars ? (
                <p className="text-xs text-muted-foreground">
                  Used amounts may be too small to appear at this scale — hover bars for exact values.
                </p>
              ) : null}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
