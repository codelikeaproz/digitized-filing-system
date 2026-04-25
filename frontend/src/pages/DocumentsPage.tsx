import React, { useState, useEffect, useCallback, useMemo } from "react";
import { FolderNavigation } from "@/components/FolderNavigation";
import { DocumentTable } from "@/components/DocumentTable";
import { UploadDialog } from "@/components/UploadDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  Search, 
  ChevronRight, 
  Home,
  FileUp,
} from "lucide-react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { useCategories } from "@/contexts/CategoryContext";
import { CategorySelect } from "@/components/CategorySelect";
import { Document as DocType } from "@/types";
import { toast } from "sonner";
import { deleteDocument } from "@/lib/document-actions";
import { useAuth } from "@/lib/auth-context";
import { api, PaginatedResponse } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { PaginationControls } from "@/components/PaginationControls";

const BACKEND_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function getPdfUrl(fileUrl?: string | null) {
  if (!fileUrl) return null;
  if (fileUrl.startsWith("/")) return `${BACKEND_URL}${fileUrl}`;

  try {
    const url = new URL(fileUrl);
    if ((url.hostname === "localhost" || url.hostname === "127.0.0.1") && url.port === "8000") {
      return `${BACKEND_URL}${url.pathname}${url.search}${url.hash}`;
    }
    return fileUrl;
  } catch {
    return `${BACKEND_URL}/${fileUrl.replace(/^\/+/, "")}`;
  }
}

function getFileNameFromDisposition(disposition: string | null) {
  if (!disposition) return null;
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]);
  const fileNameMatch = disposition.match(/filename="?([^";]+)"?/i);
  return fileNameMatch?.[1] || null;
}

async function downloadDocumentFile(document: DocType) {
  const token = localStorage.getItem("auth_token");
  const response = await fetch(`${BACKEND_URL}/api/documents/${document.id}/download/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    const text = await response.text();
    let message = response.status === 404 ? "File not found" : "Download failed";
    try {
      const data = text ? JSON.parse(text) : {};
      message = data.error || data.message || data.detail || message;
    } catch {
      if (text) message = text;
    }
    throw new Error(message);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download =
    getFileNameFromDisposition(response.headers.get("Content-Disposition")) ||
    document.file_name ||
    document.title ||
    "document.pdf";
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function flattenFolderNodes(nodes: any[]): any[] {
  return nodes.flatMap((node) => {
    const children = node.children || node.folders || [];
    const nestedFolders = flattenFolderNodes(children);
    return node.type === "folder" || node.type === "org_unit" ? [node, ...nestedFolders] : nestedFolders;
  });
}

export default function DocumentsPage() {
  const { user } = useAuth();
  const { categories } = useCategories();
  
  const [selectedFolder, setSelectedFolder] = useState<any>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<DocType | null>(null);
  const [folders, setFolders] = useState<any[]>([]);
  const [documents, setDocuments] = useState<DocType[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [flatFolders, setFlatFolders] = useState<any[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [documentCount, setDocumentCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Fetch Folders
  const fetchFolders = async () => {
    try {
      const folderTree = await api.get<any[]>("/api/folders/tree");
      setFolders(folderTree);
      setFlatFolders(flattenFolderNodes(folderTree));
    } catch (error) {
      console.error("API Error (Folders):", error);
      toast.error("Failed to load folders");
    } finally {
      setIsInitialLoading(false);
    }
  };

  useEffect(() => {
    fetchFolders();
  }, []);

  // Get path for breadcrumbs
  const getFolderPath = useCallback((folderId: string | null): any[] => {
    if (!folderId) return [];
    const path: any[] = [];
    let current = flatFolders.find(f => f.id === folderId);
    
    while (current) {
      path.unshift(current);
      const parentNodeId = current.parentId || (current.parentOrgUnitId ? `org-unit-${current.parentOrgUnitId}` : null);
      current = parentNodeId ? flatFolders.find(f => f.id === parentNodeId) : null;
    }
    return path;
  }, [flatFolders]);

  const folderPath = getFolderPath(selectedFolder?.id);
  const isVirtualFolder = Boolean(selectedFolder?.isVirtual || selectedFolder?.is_virtual);
  const isOrgUnitNode = selectedFolder?.type === "org_unit";
  const previewPdfUrl = getPdfUrl(previewDoc?.file_url);

  const handleSelectFolder = (folder: any) => {
    setSelectedFolder(folder);
    setCurrentPage(1);
  };

  const handleCategoryChange = (value: string) => {
    setCategoryFilter(value);
    setCurrentPage(1);
  };

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setCurrentPage(1);
  };

  // Fetch Documents
  const fetchDocuments = async (silent = false, searchArg?: string) => {
    if (!silent) setIsRefreshing(true);
    try {
      const params: Record<string, string | number> = {
        page: currentPage,
        page_size: pageSize,
      };
      if (selectedFolder && selectedFolder.type === "folder") params.folderId = selectedFolder.id;
      if (isOrgUnitNode && selectedFolder?.orgUnitId) params.orgUnitId = selectedFolder.orgUnitId;
      if (categoryFilter !== "all") params.category = categoryFilter;
      const effectiveSearch = searchArg !== undefined ? searchArg : debouncedSearch;
      if (effectiveSearch) params.search = effectiveSearch;
      
      const docPage = await api.get<PaginatedResponse<DocType>>("/api/documents", params);
      setDocuments(docPage.results);
      setDocumentCount(docPage.count);
    } catch (error) {
      console.error("API Error (Documents):", error);
      if (!silent) toast.error("Failed to load documents");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
    // Poll for updates if we want "pseudo-realtime" without sockets
    const interval = setInterval(() => fetchDocuments(true), 5000);
    return () => clearInterval(interval);
  }, [selectedFolder, debouncedSearch, categoryFilter, currentPage, pageSize]);

  const processedDocs = useMemo(() => {
    return documents.map(doc => {
      const categoryId = (doc as any).categoryId;
      const categoryObj = categories.find(c => c.id === categoryId);
      return {
        ...doc,
        category: categoryObj ? categoryObj.name : (doc.category || "Uncategorized")
      };
    });
  }, [documents, categories]);

  return (
    <div className="flex gap-6">
      {/* Left Sidebar: Folders */}
      <div className="w-64 flex-shrink-0 border-right pr-6 min-h-[calc(100vh-120px)]">
        <FolderNavigation 
          folders={folders} 
          onSelect={handleSelectFolder} 
          selectedId={selectedFolder?.id}
        />
      </div>

      {/* Right Content: Documents */}
      <div className="flex-1 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbLink href="#" onClick={(e) => { e.preventDefault(); handleSelectFolder(null); }}>
                    <Home className="h-4 w-4" />
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
                {isVirtualFolder ? (
                  <BreadcrumbItem>
                    <BreadcrumbPage>{selectedFolder.name}</BreadcrumbPage>
                  </BreadcrumbItem>
                ) : folderPath.length > 0 ? (
                  folderPath.map((folder, index) => (
                    <React.Fragment key={folder.id}>
                      <BreadcrumbItem>
                        {index === folderPath.length - 1 ? (
                          <BreadcrumbPage>{folder.name}</BreadcrumbPage>
                        ) : (
                          <BreadcrumbLink 
                            href="#" 
                            onClick={(e) => { e.preventDefault(); handleSelectFolder(folder); }}
                          >
                            {folder.name}
                          </BreadcrumbLink>
                        )}
                      </BreadcrumbItem>
                      {index < folderPath.length - 1 && (
                        <BreadcrumbSeparator>
                          <ChevronRight className="h-4 w-4" />
                        </BreadcrumbSeparator>
                      )}
                    </React.Fragment>
                  ))
                ) : (
                  <BreadcrumbItem>
                    <BreadcrumbPage>All Files</BreadcrumbPage>
                  </BreadcrumbItem>
                )}
              </BreadcrumbList>
            </Breadcrumb>
          </div>
          <div className="flex items-center gap-2">
            <CategorySelect 
              value={categoryFilter} 
              onValueChange={handleCategoryChange} 
              className="w-[200px]"
              showAllOption
              orgUnitId={isOrgUnitNode ? selectedFolder?.orgUnitId : selectedFolder?.orgUnitId}
            />
            <Button 
              size="sm" 
              className="gap-2 bg-brand-green hover:bg-brand-green/90 h-9"
              onClick={() => setIsUploadOpen(true)}
            >
              <FileUp className="h-4 w-4" />
              Scan/Upload
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input 
              placeholder="Search by name, code, description, keywords..." 
              className="pl-10" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div>
          {isInitialLoading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/50 backdrop-blur-sm z-10">
              <Loader2 className="h-8 w-8 animate-spin text-primary mb-2" />
              <p className="text-sm text-muted-foreground">Loading documents...</p>
            </div>
          ) : (
            <DocumentTable 
              data={processedDocs} 
              onDelete={async (doc) => {
                await deleteDocument(doc.id, doc.title, user?.id);
                fetchDocuments(true);
              }}
              onView={(doc) => setPreviewDoc(doc)}
              onDownload={async (doc) => {
                try {
                  await downloadDocumentFile(doc);
                  toast.success("Download started");
                } catch (error: any) {
                  toast.error(error.message || "Download failed");
                }
              }}
              onRename={async (doc, fileName) => {
                try {
                  await api.patch(`/api/documents/${doc.id}/rename`, { file_name: fileName });
                  toast.success("Document renamed");
                  fetchDocuments(true);
                } catch (error: any) {
                  toast.error(error.message || "Rename failed");
                  throw error;
                }
              }}
            />
          )}
          <PaginationControls
            count={documentCount}
            currentPage={currentPage}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={handlePageSizeChange}
            disabled={isInitialLoading || isRefreshing}
          />
          {isRefreshing && !isInitialLoading && (
            <div className="absolute top-2 right-2 flex items-center gap-2 bg-background/80 px-2 py-1 rounded border shadow-sm z-20">
              <Loader2 className="h-3 w-3 animate-spin text-primary" />
              <span className="text-[10px] text-muted-foreground">Updating...</span>
            </div>
          )}
        </div>
      </div>

      <UploadDialog 
        open={isUploadOpen} 
        onOpenChange={setIsUploadOpen} 
        selectedFolderId={isVirtualFolder || isOrgUnitNode ? undefined : selectedFolder?.id} 
        selectedFolderPath={isVirtualFolder ? 'All Files' : isOrgUnitNode ? selectedFolder?.name : folderPath.map(f => f.name).join(' > ') || 'All Files'}
      />

      <Dialog open={!!previewDoc} onOpenChange={(open) => !open && setPreviewDoc(null)}>
        <DialogContent className="sm:max-w-[1000px] h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <FileUp className="h-6 w-6 text-primary" />
              Document Preview
            </DialogTitle>
            <DialogDescription className="text-base">
              Viewing: <span className="font-semibold text-foreground">{previewDoc?.title}</span> ({previewDoc?.category})
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-hidden rounded-lg border bg-muted">
            {previewPdfUrl ? (
              <iframe
                src={previewPdfUrl}
                title={`PDF Preview - ${previewDoc?.title || "Document"}`}
                className="h-full min-h-[70vh] w-full bg-white"
                style={{ border: "none" }}
              />
            ) : (
              <div className="flex h-full min-h-[70vh] flex-col items-center justify-center gap-2 p-8 text-center">
                <p className="text-sm font-semibold text-foreground">No preview available</p>
                <p className="max-w-md text-sm text-muted-foreground">
                  This document does not have an uploaded file URL. Check that the file exists under the Django media folder.
                </p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
