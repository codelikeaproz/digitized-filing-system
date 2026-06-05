import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_BRAND_GREEN, CHART_BRAND_YELLOW } from "@/lib/chart-colors";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type OrgUnitCount = {
  org_unit: string;
  count: number;
};

export type AuditAnalytics = {
  uploads_by_org_unit: OrgUnitCount[];
  deletes_by_org_unit: OrgUnitCount[];
  edits_by_org_unit: OrgUnitCount[];
};

type AuditAnalyticsChartsProps = {
  analytics: AuditAnalytics | null;
  isLoading?: boolean;
};

function formatChartData(rows: OrgUnitCount[]) {
  return rows.map((row) => ({
    name: row.org_unit,
    count: row.count,
  }));
}

function AnalyticsBarChart({
  title,
  data,
  color,
}: {
  title: string;
  data: OrgUnitCount[];
  color: string;
}) {
  const chartData = formatChartData(data);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">No data for the selected filters.</p>
        ) : (
          <div className="h-[280px] w-full">
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
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill={color} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AuditAnalyticsCharts({ analytics, isLoading }: AuditAnalyticsChartsProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 lg:grid-cols-3">
        {[1, 2, 3].map((item) => (
          <Card key={item}>
            <CardContent className="h-[320px] flex items-center justify-center text-sm text-muted-foreground">
              Loading analytics...
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!analytics) {
    return null;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <AnalyticsBarChart
        title="Upload Count per Office Unit"
        data={analytics.uploads_by_org_unit}
        color={CHART_BRAND_YELLOW}
      />
      <AnalyticsBarChart
        title="Deleted Files per Office Unit"
        data={analytics.deletes_by_org_unit}
        color={CHART_BRAND_GREEN}
      />
      <AnalyticsBarChart
        title="Edited Files per Office Unit"
        data={analytics.edits_by_org_unit}
        color={CHART_BRAND_YELLOW}
      />
    </div>
  );
}
