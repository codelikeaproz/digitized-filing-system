/**
 * AuditLogsPage — system audit trail (Admin only route).
 *
 * Features: search/filter, pagination, CSV/XLSX export.
 * APIs: GET /api/audit-logs/, export-csv, export-xlsx.
 */
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
import { api, PaginatedResponse } from "@/lib/api";
import { AuditLog } from "@/types";
import { format } from "date-fns";
import { toast } from "sonner";
import { PaginationControls } from "@/components/PaginationControls";
import { formatManilaDateTime } from "@/lib/time";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

const BACKEND_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const ACTION_OPTIONS = [
  { value: "LOGIN", label: "Login" },
  { value: "UPLOAD", label: "Upload" },
  { value: "SCAN", label: "Scan" },
  { value: "DOWNLOAD_DOCUMENT", label: "Download" },
  { value: "EXPORT_AUDIT_CSV", label: "Export CSV" },
  { value: "EXPORT_AUDIT_XLSX", label: "Export Excel" },
  { value: "CREATE_USER", label: "Create User" },
  { value: "SEND_ACTIVATION_EMAIL", label: "Send Activation Email" },
  { value: "ACTIVATE_ACCOUNT", label: "Activate Account" },
  { value: "UPDATE_USER", label: "Update User" },
  { value: "DEACTIVATE_USER", label: "Deactivate User" },
  { value: "ACTIVATE_USER", label: "Activate User" },
  { value: "DELETE_USER", label: "Delete User" },
  { value: "PASSWORD_RESET_REQUEST", label: "Password Reset Request" },
  { value: "PASSWORD_RESET_SUCCESS", label: "Password Reset Success" },
  { value: "RENAME_FOLDER", label: "Rename Folder" },
  { value: "RENAME_DOCUMENT", label: "Rename Document" },
  { value: "EDIT_DOCUMENT", label: "Edit Document" },
  { value: "DELETE_FOLDER", label: "Delete Folder" },
  { value: "RESTORE_FOLDER", label: "Restore Folder" },
  { value: "PERMANENT_DELETE_FOLDER", label: "Permanent Delete Folder" },
  { value: "CREATE_ORG_TYPE", label: "Create Org Type" },
  { value: "UPDATE_ORG_TYPE", label: "Update Org Type" },
  { value: "DELETE_ORG_TYPE", label: "Delete Org Type" },
  { value: "CREATE_ORG_UNIT", label: "Create Org Unit" },
  { value: "UPDATE_ORG_UNIT", label: "Update Org Unit" },
  { value: "DELETE_ORG_UNIT", label: "Delete Org Unit" },
  { value: "CREATE_CATEGORY", label: "Create Category" },
  { value: "UPDATE_CATEGORY", label: "Update Category" },
  { value: "DELETE_CATEGORY", label: "Delete Category" },
];

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");
  const [orgUnitFilter, setOrgUnitFilter] = useState("all");
  const [orgUnits, setOrgUnits] = useState<{ id: string; name: string }[]>([]);
  const [logCount, setLogCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(true);
  const [isDateRangeOpen, setIsDateRangeOpen] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [draftStartDate, setDraftStartDate] = useState("");
  const [draftEndDate, setDraftEndDate] = useState("");
  const [isExporting, setIsExporting] = useState(false);

  const buildFilterParams = (includePagination = true) => {
    const params: Record<string, string | number> = {};
    if (includePagination) {
      params.page = currentPage;
      params.page_size = pageSize;
    }
    if (debouncedSearch) params.search = debouncedSearch;
    if (actionFilter !== "all") params.action = actionFilter;
    if (roleFilter !== "all") params.role = roleFilter;
    if (orgUnitFilter !== "all") params.org_unit = orgUnitFilter;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    return params;
  };

  const fetchLogs = async () => {
    try {
      const logPage = await api.get<PaginatedResponse<AuditLog>>("/api/audit-logs/", buildFilterParams());
      setLogs(logPage.results);
      setLogCount(logPage.count);
    } catch (error) {
      console.error("API Error (Audit Logs):", error);
      toast.error("Failed to load audit logs");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchOrgUnits = async () => {
    try {
      const data = await api.get<PaginatedResponse<{ id: string; name: string }>>("/api/org-units/", { page_size: 100 });
      setOrgUnits(data.results);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 10000);
    return () => clearInterval(interval);
  }, [currentPage, pageSize, debouncedSearch, actionFilter, roleFilter, orgUnitFilter, startDate, endDate]);

  useEffect(() => {
    fetchOrgUnits();
  }, []);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setCurrentPage(1);
  };

  const handleFilterChange = (setter: (value: string) => void, value: string) => {
    setter(value);
    setCurrentPage(1);
  };

  const openDateRange = () => {
    setDraftStartDate(startDate);
    setDraftEndDate(endDate);
    setIsDateRangeOpen(true);
  };

  const applyDateRange = () => {
    setStartDate(draftStartDate);
    setEndDate(draftEndDate);
    setCurrentPage(1);
    setIsDateRangeOpen(false);
  };

  const clearDateRange = () => {
    setDraftStartDate("");
    setDraftEndDate("");
    setStartDate("");
    setEndDate("");
    setCurrentPage(1);
    setIsDateRangeOpen(false);
  };

  const getDateRangeLabel = () => {
    if (!startDate && !endDate) return "Date Range";
    const formatShortDate = (value: string) => format(new Date(`${value}T00:00:00`), "MMM d, yyyy");
    if (startDate && endDate) return `${formatShortDate(startDate)} - ${formatShortDate(endDate)}`;
    if (startDate) return `From ${formatShortDate(startDate)}`;
    return `Until ${formatShortDate(endDate)}`;
  };

  const handleExportXlsx = async () => {
    setIsExporting(true);
    try {
      const query = new URLSearchParams();
      Object.entries(buildFilterParams(false)).forEach(([key, value]) => {
        query.set(key, String(value));
      });
      const url = `${BACKEND_URL}/api/audit-logs/export-xlsx/${query.toString() ? `?${query.toString()}` : ""}`;
      const token = localStorage.getItem("auth_token");
      const response = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "Failed to export audit logs");
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = downloadUrl;
      link.download = `audit_logs_${new Date().toISOString().slice(0, 10)}.xlsx`;
      window.document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      toast.success("Audit logs Excel exported");
    } catch (error: any) {
      toast.error(error.message || "Failed to export audit logs");
    } finally {
      setIsExporting(false);
    }
  };

  const formatActionStr = (action: string) => {
    const actionOption = ACTION_OPTIONS.find(option => option.value === action);
    if (actionOption) return actionOption.label;
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
      case 'UPLOAD': return <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700">{formattedAction}</Badge>;
      case 'SCAN': return <Badge variant="outline" className="border-cyan-200 bg-cyan-50 text-cyan-700 font-bold">{formattedAction}</Badge>;
      case 'Routing': return <Badge variant="outline" className="border-purple-200 bg-purple-50 text-purple-700">{formattedAction}</Badge>;
      case 'DOWNLOAD_DOCUMENT': return <Badge variant="outline" className="border-orange-200 bg-orange-50 text-orange-700">{formattedAction}</Badge>;
      case 'EXPORT_AUDIT_CSV':
      case 'EXPORT_AUDIT_XLSX': return <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">{formattedAction}</Badge>;
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
            title="Action"
            name="action"
            value={actionFilter}
            onChange={(e) => handleFilterChange(setActionFilter, e.target.value)}
            className="h-9 px-3 py-1 rounded-md border border-input text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="all">All Actions</option>
            {ACTION_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <select
            title="Role"
            value={roleFilter}
            onChange={(e) => handleFilterChange(setRoleFilter, e.target.value)}
            className="h-9 px-3 py-1 rounded-md border border-input text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="all">All Roles</option>
            <option value="admin">Admin</option>
            <option value="dept_head">Dept Head</option>
            <option value="staff">Staff</option>
          </select>
          <select
            title="Org Unit"
            value={orgUnitFilter}
            onChange={(e) => handleFilterChange(setOrgUnitFilter, e.target.value)}
            className="h-9 px-3 py-1 rounded-md border border-input text-sm focus:outline-none focus:ring-1 focus:ring-ring max-w-[150px]"
          >
            <option value="all">All Org Units</option>
            <option value="Global Access">Global Access</option>
            {orgUnits.map(ou => (
              <option key={ou.id} value={ou.name}>{ou.name}</option>
            ))}
          </select>
          <Button
            variant={startDate || endDate ? "default" : "outline"}
            className="gap-2 h-9 px-3 py-1 rounded-md text-sm font-normal"
            onClick={openDateRange}
          >
            <Calendar className="h-4 w-4" />
            {getDateRangeLabel()}
          </Button>
          <Button
            variant="outline"
            className="gap-2 h-9 px-3 py-1 rounded-md text-sm font-normal"
            onClick={handleExportXlsx}
            disabled={isExporting}
          >
            {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            {isExporting ? "Exporting..." : "Export Excel"}
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
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-[#0A4D27]" />
                  Loading logs...
                </TableCell>
              </TableRow>
            ) : logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  No logs found.
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="font-mono text-xs text-muted-foreground">{formatManilaDateTime(log.createdAt)}</TableCell>
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
        <PaginationControls
          count={logCount}
          currentPage={currentPage}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={handlePageSizeChange}
          disabled={isLoading}
        />
      </div>

      <Dialog open={isDateRangeOpen} onOpenChange={setIsDateRangeOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Filter by Date Range</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="audit-start-date">Start Date</Label>
              <Input
                id="audit-start-date"
                type="date"
                value={draftStartDate}
                onChange={(event) => setDraftStartDate(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="audit-end-date">End Date</Label>
              <Input
                id="audit-end-date"
                type="date"
                value={draftEndDate}
                onChange={(event) => setDraftEndDate(event.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={clearDateRange}>
              Clear
            </Button>
            <Button onClick={applyDateRange}>
              Apply
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
