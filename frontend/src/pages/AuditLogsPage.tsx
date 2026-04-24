import React, { useState, useEffect } from "react";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, History, Download, Filter, Calendar, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { AuditLog } from "@/types";
import { format } from "date-fns";
import { toast } from "sonner";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");
  const [orgUnitFilter, setOrgUnitFilter] = useState("all");
  const [isLoading, setIsLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      const logList = await api.get<AuditLog[]>("/api/audit-logs");
      // Sort by date descending
      logList.sort((a, b) => new Date(b.createdAt as string).getTime() - new Date(a.createdAt as string).getTime());
      setLogs(logList);
    } catch (error) {
      console.error("API Error (Audit Logs):", error);
      toast.error("Failed to load audit logs");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 10000);
    return () => clearInterval(interval);
  }, []);

  const filteredLogs = logs.filter((log: any) => {
    const matchesSearch = log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          log.details.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          log.userId?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          log.userFullName?.toLowerCase().includes(searchQuery.toLowerCase());
                          
    const matchesAction = actionFilter === 'all' || log.action === actionFilter;
    const matchesRole = roleFilter === 'all' || Math.abs(log.userRole?.localeCompare(roleFilter, undefined, { sensitivity: 'base' })) === 0;
    const matchesOrgUnit = orgUnitFilter === 'all' || log.displayOrgUnit === orgUnitFilter || (log.displayOrgUnit || "Global Access") === orgUnitFilter;

    return matchesSearch && matchesAction && matchesRole && matchesOrgUnit;
  });

  const uniqueActions = Array.from(new Set([
    ...logs.map(l => l.action).filter(Boolean),
    "CREATE_USER",
    "UPDATE_USER",
    "RENAME_FOLDER",
    "RENAME_DOCUMENT",
    "UPDATE_ORG_UNIT",
    "UPDATE_CATEGORY"
  ]));
  const uniqueRoles = Array.from(new Set(logs.map((l: any) => l.userRole).filter(Boolean)));
  const uniqueOrgUnits = Array.from(new Set(logs.map((l: any) => l.displayOrgUnit || "Global Access").filter(Boolean)));

  const formatDate = (date: any) => {
    if (!date) return "-";
    try {
      const d = new Date(date);
      return format(d, "MMM dd, yyyy HH:mm:ss");
    } catch (e) {
      return String(date);
    }
  };

  const formatActionStr = (action: string) => {
    if (!action) return 'Unknown';
    return action
      .toLowerCase()
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getActionBadge = (action: string) => {
    const formattedAction = formatActionStr(action);
    switch (action) {
      case 'LOGIN': 
      case 'Login': return <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">{formattedAction}</Badge>;
      case 'Upload': return <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700">{formattedAction}</Badge>;
      case 'SCAN': return <Badge variant="outline" className="border-cyan-200 bg-cyan-50 text-cyan-700 font-bold">{formattedAction}</Badge>;
      case 'Routing': return <Badge variant="outline" className="border-purple-200 bg-purple-50 text-purple-700">{formattedAction}</Badge>;
      case 'Download': return <Badge variant="outline" className="border-orange-200 bg-orange-50 text-orange-700">{formattedAction}</Badge>;
      default: return <Badge variant="outline">{formattedAction}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <History className="h-6 w-6 text-primary" />
          <h2 className="text-3xl font-bold tracking-tight">Audit Logs</h2>
        </div>
        <p className="text-muted-foreground">Detailed history of all system events and user actions.</p>
      </div>

      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input 
            placeholder="Search logs by user or action..." 
            className="pl-10" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="h-9 px-3 py-1 rounded-md border border-input text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="all">All Actions</option>
            {uniqueActions.map(a => (
              <option key={a} value={a}>{formatActionStr(a)}</option>
            ))}
          </select>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="h-9 px-3 py-1 rounded-md border border-input text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="all">All Roles</option>
            {uniqueRoles.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <select
            value={orgUnitFilter}
            onChange={(e) => setOrgUnitFilter(e.target.value)}
            className="h-9 px-3 py-1 rounded-md border border-input text-sm focus:outline-none focus:ring-1 focus:ring-ring max-w-[150px]"
          >
            <option value="all">All Org Units</option>
            {uniqueOrgUnits.map(ou => (
              <option key={ou} value={ou}>{ou}</option>
            ))}
          </select>
          <Button variant="outline" className="gap-2 h-9 px-3 py-1 rounded-md text-sm font-normal">
            <Calendar className="h-4 w-4" />
            Date Range
          </Button>
          <Button variant="outline" className="gap-2 h-9 px-3 py-1 rounded-md text-sm font-normal">
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
        </div>
      </div>

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">Timestamp</TableHead>
              <TableHead className="w-[150px]">Name</TableHead>
              <TableHead className="w-[100px]">Role</TableHead>
              <TableHead className="w-[150px]">Org Unit</TableHead>
              <TableHead className="w-[120px]">Action</TableHead>
              <TableHead>Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredLogs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  No logs found.
                </TableCell>
              </TableRow>
            ) : (
              filteredLogs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="font-mono text-xs text-muted-foreground">{formatDate(log.createdAt)}</TableCell>
                  <TableCell className="font-medium text-sm">
                    {(log as any).userFullName || "System"}
                  </TableCell>
                  <TableCell>
                    <span className="text-xs bg-muted/50 px-2 py-1 rounded-md">
                      {(log as any).userRole || log.userId || "System"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs text-muted-foreground font-medium">
                      {(log as any).displayOrgUnit || "Global Access"}
                    </span>
                  </TableCell>
                  <TableCell>{getActionBadge(log.action)}</TableCell>
                  <TableCell className="text-sm">{log.details}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
