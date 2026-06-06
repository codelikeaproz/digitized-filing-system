/**
 * DashboardPage — filing statistics, storage utilization, and Office Unit filter.
 *
 * API: GET /api/dashboard/?office_unit=all|{id}
 */
import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Files,
  UploadCloud,
  Building2,
  Loader2,
  Users,
  Trash2,
} from "lucide-react";
import { api, PaginatedResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  StorageUtilizationChart,
  type StorageStats,
} from "@/components/dashboard/StorageUtilizationChart";
import {
  OfficeUnitStorageComparisonChart,
  type OfficeUnitStorageRow,
} from "@/components/dashboard/OfficeUnitStorageComparisonChart";


type DashboardResponse = {
  scope: "global" | "office_unit";
  office_unit_id: string | null;
  office_unit_name: string;
  office_unit_filter: string;
  can_filter_office_units: boolean;
  total_documents: number;
  uploaded_files: number;
  total_org_units?: number | null;
  total_users?: number | null;
  deleted_files?: number | null;
  storage?: StorageStats | null;
  storage_by_office_unit: OfficeUnitStorageRow[];
};

type StatCard = {
  title: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
};

type OrgUnitOption = { id: string; name: string };

export default function DashboardPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [officeUnitFilter, setOfficeUnitFilter] = useState("all");
  const [orgUnits, setOrgUnits] = useState<OrgUnitOption[]>([]);
  const [stats, setStats] = useState<StatCard[]>([]);
  const [storage, setStorage] = useState<StorageStats | null>(null);
  const [storageComparison, setStorageComparison] = useState<OfficeUnitStorageRow[]>([]);
  const [dashboardScope, setDashboardScope] = useState<"global" | "office_unit">("global");
  const [officeUnitLabel, setOfficeUnitLabel] = useState("All Office Units");
  const [canFilter, setCanFilter] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isAdmin && !canFilter) return;
    const fetchOrgUnits = async () => {
      try {
        const data = await api.get<PaginatedResponse<OrgUnitOption>>("/api/org-units/", {
          page_size: 100,
        });
        setOrgUnits(data.results);
      } catch (error) {
        console.error("Failed to load Office Units for dashboard filter:", error);
      }
    };
    fetchOrgUnits();
  }, [canFilter, isAdmin]);

  const buildStatCards = (data: DashboardResponse): StatCard[] => {
    if (data.scope === "global") {
      const cards: StatCard[] = [
        {
          title: "Total Documents",
          value: data.total_documents.toString(),
          icon: Files,
          color: "text-blue-600",
        },
        {
          title: "Uploaded Files",
          value: data.uploaded_files.toString(),
          icon: UploadCloud,
          color: "text-indigo-600",
        },
      ];
      if (isAdmin) {
        cards.push({
          title: "Total Office Units",
          value: (data.total_org_units || 0).toString(),
          icon: Building2,
          color: "text-emerald-600",
        });
        cards.push({
          title: "Total Users",
          value: (data.total_users || 0).toString(),
          icon: Users,
          color: "text-orange-600",
        });
      }
      return cards;
    }

    const cards: StatCard[] = [
      {
        title: "Documents",
        value: data.total_documents.toString(),
        icon: Files,
        color: "text-blue-600",
      },
      {
        title: "Uploaded Files",
        value: data.uploaded_files.toString(),
        icon: UploadCloud,
        color: "text-indigo-600",
      },
      {
        title: "Users",
        value: (data.total_users || 0).toString(),
        icon: Users,
        color: "text-orange-600",
      },
      {
        title: "Deleted Files",
        value: (data.deleted_files || 0).toString(),
        icon: Trash2,
        color: "text-red-600",
      },
    ];
    return cards;
  };

  const fetchStats = useCallback(async () => {
    try {
      setIsLoading(true);
      const params: Record<string, string> = {};
      if (canFilter && officeUnitFilter !== "all") {
        params.office_unit = officeUnitFilter;
      } else if (isAdmin) {
        params.office_unit = "all";
      }

      const data = await api.get<DashboardResponse>("/api/dashboard/", params);
      setStats(buildStatCards(data));
      setStorage(data.storage || null);
      setStorageComparison(data.storage_by_office_unit || []);
      setDashboardScope(data.scope);
      setOfficeUnitLabel(data.office_unit_name);
      setCanFilter(data.can_filter_office_units);
    } catch (error) {
      console.error("Dashboard Stats Error:", error);
    } finally {
      setIsLoading(false);
    }
  }, [isAdmin, officeUnitFilter, canFilter]);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const gridCols =
    stats.length >= 5
      ? "lg:grid-cols-5"
      : stats.length === 4
        ? "lg:grid-cols-4"
        : stats.length === 3
          ? "lg:grid-cols-3"
          : "lg:grid-cols-2";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-2">
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Welcome back. Here's what's happening in your organization.
          </p>
        </div>

        {canFilter ? (
          <div className="flex flex-col gap-1 min-w-[220px]">
            <label htmlFor="dashboard-office-unit" className="text-sm font-medium text-gray-700">
              Office Unit
            </label>
            <select
              id="dashboard-office-unit"
              title="Filter dashboard by Office Unit"
              value={officeUnitFilter}
              onChange={(e) => setOfficeUnitFilter(e.target.value)}
              className="flex h-11 w-full items-center rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              <option value="all">All Office Units</option>
              {orgUnits.map((ou) => (
                <option key={ou.id} value={ou.id}>
                  {ou.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          !isAdmin && (
            <div className="text-sm text-muted-foreground rounded-xl border px-4 py-2 bg-muted/30">
              Office Unit: <span className="font-semibold text-foreground">{officeUnitLabel}</span>
            </div>
          )
        )}
      </div>

      <div className={`grid gap-4 grid-cols-1 sm:grid-cols-2 ${gridCols} relative`}>
        {isLoading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/50 backdrop-blur-[1px]">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        )}
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {storage && <StorageUtilizationChart storage={storage} isGlobal={dashboardScope === "global"} />}

      {storageComparison.length > 0 && (
        <OfficeUnitStorageComparisonChart
          data={storageComparison}
          totalUsedMb={storage?.used_mb}
          totalQuotaMb={dashboardScope === "global" ? storage?.org_units_quota_mb : storage?.quota_mb}
        />
      )}
    </div>
  );
}
