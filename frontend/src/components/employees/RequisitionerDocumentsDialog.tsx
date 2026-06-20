import { useCallback, useEffect, useState } from "react";
import { Eye, FileText, Loader2, MoreVertical, Search } from "lucide-react";
import { toast } from "sonner";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PaginationControls } from "@/components/PaginationControls";
import { api } from "@/lib/api";
import { resolveApiUrl } from "@/lib/api-base-url";
import { formatRequisitionerEmployeeNumberDisplay } from "@/lib/employee-number";
import { cn } from "@/lib/utils";
import type { DocType, EmployeeDirectoryEntry, RequisitionerDocumentsResponse } from "@/types";

interface RequisitionerDocumentsDialogProps {
  employee: EmployeeDirectoryEntry | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type RequisitionerTaggedDocumentLike = RequisitionerDocumentsResponse["results"][number];

export function RequisitionerDocumentsDialog({
  employee,
  open,
  onOpenChange,
}: RequisitionerDocumentsDialogProps) {
  const [documents, setDocuments] = useState<RequisitionerTaggedDocumentLike[]>([]);
  const [documentCount, setDocumentCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<DocType | null>(null);
  const [previewBlobUrl, setPreviewBlobUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setCurrentPage(1);
      setSearchQuery("");
      setPreviewDoc(null);
    }
  }, [open]);

  useEffect(() => {
    setCurrentPage(1);
  }, [employee?.id, searchQuery]);

  const fetchDocuments = useCallback(async () => {
    if (!employee) return;
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        page: currentPage,
        page_size: pageSize,
      };
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }
      const data = await api.get<RequisitionerDocumentsResponse>(
        `/api/employees/${employee.id}/documents`,
        params,
      );
      setDocuments(data.results);
      setDocumentCount(data.count);
    } catch (error: any) {
      toast.error(error.message || "Failed to load tagged documents");
    } finally {
      setLoading(false);
    }
  }, [employee, currentPage, pageSize, searchQuery]);

  useEffect(() => {
    if (!open || !employee) return;
    const timer = setTimeout(() => {
      fetchDocuments();
    }, 300);
    return () => clearTimeout(timer);
  }, [open, employee, fetchDocuments]);

  useEffect(() => {
    if (!previewDoc) {
      setPreviewBlobUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return null;
      });
      setPreviewLoading(false);
      setPreviewError(null);
      return;
    }

    let cancelled = false;
    setPreviewLoading(true);
    setPreviewError(null);

    const loadPreview = async () => {
      try {
        const token = localStorage.getItem("auth_token");
        const response = await fetch(resolveApiUrl(`/api/documents/${previewDoc.id}/preview/`), {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (!response.ok) {
          const text = await response.text();
          let message = response.status === 404 ? "Preview not available" : "Preview failed";
          try {
            const data = text ? JSON.parse(text) : {};
            message = data.error || data.message || data.detail || message;
          } catch {
            if (text && !text.includes("<!DOCTYPE")) message = text.slice(0, 200);
          }
          throw new Error(message);
        }

        const contentType = response.headers.get("Content-Type") || "";
        if (contentType.includes("application/json")) {
          const data = await response.json();
          if (data.googleDriveLink) {
            window.open(data.googleDriveLink, "_blank", "noopener,noreferrer");
            if (!cancelled) setPreviewLoading(false);
            return;
          }
        }

        if (!contentType.includes("application/pdf") && !contentType.includes("octet-stream")) {
          throw new Error("Preview failed — server did not return a PDF.");
        }

        const blob = await response.blob();
        if (cancelled) return;
        const objectUrl = URL.createObjectURL(blob);
        setPreviewBlobUrl((previous) => {
          if (previous) URL.revokeObjectURL(previous);
          return objectUrl;
        });
      } catch (error: any) {
        if (!cancelled) {
          setPreviewError(error.message || "Failed to load preview");
          setPreviewBlobUrl((previous) => {
            if (previous) URL.revokeObjectURL(previous);
            return null;
          });
        }
      } finally {
        if (!cancelled) setPreviewLoading(false);
      }
    };

    loadPreview();
    return () => {
      cancelled = true;
    };
  }, [previewDoc]);

  const handleViewDocument = async (documentId: string) => {
    try {
      const document = await api.get<DocType>(`/api/documents/${documentId}`);
      setPreviewDoc(document);
    } catch (error: any) {
      toast.error(error.message || "Failed to open document preview");
    }
  };

  if (!employee) return null;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent size="xl" className="flex max-h-[90vh] flex-col gap-4 overflow-hidden">
          <DialogHeader>
            <DialogTitle>Tagged Documents</DialogTitle>
          </DialogHeader>

          <div className="rounded-lg border bg-muted/30 p-4">
            <div className="text-sm text-muted-foreground">Requisitioner</div>
            <div className="text-sm text-muted-foreground">
              {formatRequisitionerEmployeeNumberDisplay(employee.employeeNumber)}
            </div>
            <div className="text-lg font-semibold">{employee.fullName}</div>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search by document title or code..."
              className="pl-9"
            />
          </div>

          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border">
            <div className="min-h-[420px] flex-1 overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[220px]">Document Title</TableHead>
                    <TableHead className="whitespace-nowrap">Category</TableHead>
                    <TableHead className="whitespace-nowrap">Office Unit</TableHead>
                    <TableHead className="whitespace-nowrap">Date Uploaded</TableHead>
                    <TableHead className="w-[72px] text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="h-24 text-center">
                        <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
                      </TableCell>
                    </TableRow>
                  ) : documents.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                        No tagged documents found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    documents.map((document) => (
                      <TableRow key={document.id}>
                        <TableCell className="min-w-[220px]">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <div className="min-w-0">
                              <div className="font-medium break-words">{document.title}</div>
                              {document.keywords && document.keywords.length > 0 && (
                                <div className="text-xs text-muted-foreground break-words">
                                  {document.keywords.join(", ")}
                                </div>
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="whitespace-nowrap">{document.category}</TableCell>
                        <TableCell className="whitespace-nowrap">{document.orgUnit}</TableCell>
                        <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                          {document.uploadedAt}
                        </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger
                              className={cn(buttonVariants({ variant: "ghost" }), "h-8 w-8 p-0")}
                            >
                              <MoreVertical className="h-4 w-4" />
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => handleViewDocument(document.id)}>
                                <Eye className="mr-2 h-4 w-4 text-blue-600" />
                                View
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
            <PaginationControls
              count={documentCount}
              currentPage={currentPage}
              pageSize={pageSize}
              onPageChange={setCurrentPage}
              onPageSizeChange={(nextPageSize) => {
                setPageSize(nextPageSize);
                setCurrentPage(1);
              }}
              disabled={loading}
            />
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!previewDoc} onOpenChange={(nextOpen) => !nextOpen && setPreviewDoc(null)}>
        <DialogContent size="xl" className="flex max-h-[90vh] flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Document Preview</DialogTitle>
          </DialogHeader>
          <div className="text-sm text-muted-foreground">
            Viewing: <span className="font-semibold text-foreground">{previewDoc?.title}</span>
          </div>
          <div className="min-h-[520px] overflow-hidden rounded-md border bg-muted/20">
            {previewLoading ? (
              <div className="flex h-[520px] items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : previewError ? (
              <div className="flex h-[520px] items-center justify-center px-6 text-center text-sm text-muted-foreground">
                {previewError}
              </div>
            ) : previewBlobUrl ? (
              <iframe
                src={previewBlobUrl}
                title={`PDF Preview - ${previewDoc?.title || "Document"}`}
                className="h-[520px] w-full"
              />
            ) : (
              <div className="flex h-[520px] items-center justify-center text-sm text-muted-foreground">
                No preview available.
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
