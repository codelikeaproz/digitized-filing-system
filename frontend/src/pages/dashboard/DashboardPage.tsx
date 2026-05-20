// Dashboard page for viewing filing system statistics.
import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Files, UploadCloud, Scan, Building2, Loader2, Users } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const SCANNER_ENABLED = import.meta.env.VITE_ENABLE_SCANNER === "true";

type DashboardStats = {
  total_documents: number;
  uploaded_files: number;
  scanned_files: number;
  total_org_units?: number;
  total_users?: number;
};

export default function DashboardPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [stats, setStats] = useState([
    { title: "Total Documents", value: "0", icon: Files, color: "text-blue-600" },
    { title: "Uploaded Files", value: "0", icon: UploadCloud, color: "text-indigo-600" },
    ...(SCANNER_ENABLED ? [{ title: "Scanned Files", value: "0", icon: Scan, color: "text-purple-600" }] : []),
  ]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.get<DashboardStats>("/api/dashboard/stats");
        
        let newStats = [
          { title: "Total Documents", value: data.total_documents.toString(), icon: Files, color: "text-blue-600" },
          { title: "Uploaded Files", value: data.uploaded_files.toString(), icon: UploadCloud, color: "text-indigo-600" },
          ...(SCANNER_ENABLED ? [{ title: "Scanned Files", value: data.scanned_files.toString(), icon: Scan, color: "text-purple-600" }] : []),
        ];

        if (isAdmin) {
          newStats.push({ title: "Total Org Units", value: (data.total_org_units || 0).toString(), icon: Building2, color: "text-emerald-600" });
          newStats.push({ title: "Total Users", value: (data.total_users || 0).toString(), icon: Users, color: "text-orange-600" });
        }

        setStats(newStats);
      } catch (error) {
        console.error("Dashboard Stats Error:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
    // Refresh every 30 seconds for live feel
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [isAdmin]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Welcome back. Here's what's happening in your organization.</p>
      </div>

      <div className={`grid gap-4 grid-cols-1 sm:grid-cols-2 ${isAdmin ? (SCANNER_ENABLED ? 'lg:grid-cols-5' : 'lg:grid-cols-4') : (SCANNER_ENABLED ? 'lg:grid-cols-3' : 'lg:grid-cols-2')} relative`}>
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
    </div>
  );
}

