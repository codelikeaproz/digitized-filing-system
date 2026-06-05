import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_BRAND_GREEN, CHART_BRAND_YELLOW } from "@/lib/chart-colors";
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
};

type OfficeUnitStorageComparisonChartProps = {
  data: OfficeUnitStorageRow[];
};

export function OfficeUnitStorageComparisonChart({ data }: OfficeUnitStorageComparisonChartProps) {
  const chartData = data.map((row) => ({
    name: row.org_unit_name,
    used_mb: row.used_mb,
    quota_mb: row.quota_mb,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Office Unit Storage Comparison</CardTitle>
        <p className="text-xs text-muted-foreground">
          Used vs allocated quota per Office Unit — identify high consumers and nearly full units.
        </p>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">No Office Units to compare.</p>
        ) : (
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
                <Tooltip formatter={(value) => formatStorageMbWithGb(Number(value || 0))} />
                <Legend />
                <Bar dataKey="used_mb" name="Used" fill={CHART_BRAND_YELLOW} radius={[4, 4, 0, 0]} />
                <Bar dataKey="quota_mb" name="Quota" fill={CHART_BRAND_GREEN} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
