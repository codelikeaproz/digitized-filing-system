/**
 * RecycleBinPage — soft-deleted folders and documents (Admin, Dept Head).
 *
 * Staff cannot access this page. Supports restore and permanent delete.
 * APIs: GET /api/recycle-bin, POST restore, POST permanent delete with typed confirmation,
 * POST bulk-summary, bulk-restore, bulk-delete.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { api, PaginatedResponse } from '@/lib/api';
import { toast } from 'sonner';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { FileText, Folder, RefreshCcw, Trash } from 'lucide-react';
import { PermanentDeleteConfirmDialog } from '@/components/recyclebin/PermanentDeleteConfirmDialog';
import { BulkRestoreConfirmDialog } from '@/components/recyclebin/BulkRestoreConfirmDialog';
import { BulkPermanentDeleteConfirmDialog } from '@/components/recyclebin/BulkPermanentDeleteConfirmDialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PaginationControls } from '@/components/PaginationControls';
import { formatManilaDateTime } from '@/lib/time';

interface RecycleBinItem {
  id: string;
  type: 'document' | 'folder';
  name?: string;
  title?: string;
  file_size?: number;
  deletedAt?: string;
  deletedBy?: string;
  deletedByFullName?: string;
  deletedByRole?: string;
  orgUnitName?: string;
  locationPath?: string;
  filePath?: string;
  location?: string;
}

function getRecycleBinLocation(item: RecycleBinItem): string {
  return item.locationPath || item.filePath || item.location || '—';
}

function getItemKey(item: Pick<RecycleBinItem, 'type' | 'id'>) {
  return `${item.type}:${item.id}`;
}

function itemToPayload(item: RecycleBinItem) {
  return { type: item.type, id: item.id };
}

export default function RecycleBinPage() {
  const [items, setItems] = useState<RecycleBinItem[]>([]);
  const [itemCount, setItemCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'documents' | 'folders'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedItemsMap, setSelectedItemsMap] = useState<Map<string, RecycleBinItem>>(new Map());

  const [itemToRestore, setItemToRestore] = useState<RecycleBinItem | null>(null);
  const [itemToDelete, setItemToDelete] = useState<RecycleBinItem | null>(null);
  const [showBulkRestore, setShowBulkRestore] = useState(false);
  const [showBulkDelete, setShowBulkDelete] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const selectedItems = useMemo(() => Array.from(selectedItemsMap.values()), [selectedItemsMap]);

  const selectedOnPageCount = items.filter((item) => selectedItemsMap.has(getItemKey(item))).length;
  const allOnPageSelected = items.length > 0 && selectedOnPageCount === items.length;
  const someOnPageSelected = selectedOnPageCount > 0 && !allOnPageSelected;

  const selectedDocumentCount = selectedItems.filter((item) => item.type === 'document').length;
  const selectedFolderCount = selectedItems.filter((item) => item.type === 'folder').length;

  const fetchRecycleBin = async () => {
    setIsLoading(true);
    try {
      const data = await api.get<PaginatedResponse<RecycleBinItem>>('/api/recycle-bin', {
        page: currentPage,
        page_size: pageSize,
        type: filter,
      });
      setItems(data.results);
      setItemCount(data.count);
    } catch (error: any) {
      toast.error('Failed to load recycle bin');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecycleBin();
  }, [currentPage, pageSize, filter]);

  const clearSelection = () => setSelectedItemsMap(new Map());

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setCurrentPage(1);
    clearSelection();
  };

  const handleFilterChange = (value: 'all' | 'documents' | 'folders' | null) => {
    if (!value) return;
    setFilter(value);
    setCurrentPage(1);
    clearSelection();
  };

  const toggleItemSelection = (item: RecycleBinItem, checked: boolean) => {
    setSelectedItemsMap((prev) => {
      const next = new Map(prev);
      const key = getItemKey(item);
      if (checked) {
        next.set(key, item);
      } else {
        next.delete(key);
      }
      return next;
    });
  };

  const toggleSelectAllOnPage = (checked: boolean) => {
    setSelectedItemsMap((prev) => {
      const next = new Map(prev);
      if (checked) {
        items.forEach((item) => next.set(getItemKey(item), item));
      } else {
        items.forEach((item) => next.delete(getItemKey(item)));
      }
      return next;
    });
  };

  const handleRestore = async () => {
    if (!itemToRestore) return;
    setIsProcessing(true);
    try {
      await api.post('/api/recycle-bin/restore', {
        type: itemToRestore.type,
        id: itemToRestore.id
      });
      toast.success(`${itemToRestore.type === 'folder' ? 'Folder' : 'Document'} restored successfully`);
      await fetchRecycleBin();
    } catch (error: any) {
      toast.error(error.message || 'Failed to restore item');
    } finally {
      setIsProcessing(false);
      setItemToRestore(null);
    }
  };

  const handleDelete = async (confirmation: string) => {
    if (!itemToDelete) return;
    setIsProcessing(true);
    try {
      await api.post('/api/recycle-bin/delete', {
        type: itemToDelete.type,
        id: itemToDelete.id,
        confirmation,
      });
      toast.success(`${itemToDelete.type === 'folder' ? 'Folder' : 'Document'} permanently deleted`);
      await fetchRecycleBin();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete item permanently');
    } finally {
      setIsProcessing(false);
      setItemToDelete(null);
    }
  };

  const handleBulkRestore = async () => {
    if (selectedItems.length === 0) return;
    setIsProcessing(true);
    try {
      const response = await api.post<{ message: string; total_restored: number }>(
        '/api/recycle-bin/bulk-restore',
        { items: selectedItems.map(itemToPayload) }
      );
      toast.success(response.message || `${response.total_restored} items restored successfully.`);
      clearSelection();
      await fetchRecycleBin();
    } catch (error: any) {
      toast.error(error.message || 'Failed to restore selected items');
    } finally {
      setIsProcessing(false);
      setShowBulkRestore(false);
    }
  };

  const handleBulkDelete = async (confirmation: string) => {
    if (selectedItems.length === 0) return;
    setIsProcessing(true);
    try {
      const response = await api.post<{ message: string; total_deleted: number }>(
        '/api/recycle-bin/bulk-delete',
        {
          items: selectedItems.map(itemToPayload),
          confirmation,
        }
      );
      toast.success(response.message || `${response.total_deleted} items permanently deleted.`);
      clearSelection();
      await fetchRecycleBin();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete selected items permanently');
    } finally {
      setIsProcessing(false);
      setShowBulkDelete(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Trash className="h-6 w-6 text-primary" />
            <h2 className="text-3xl font-bold tracking-tight">Recycle Bin</h2>
          </div>
          <p className="text-muted-foreground">Manage and restore deleted documents and folders.</p>
        </div>

        <div className="flex items-center gap-4">
          <Select value={filter} onValueChange={handleFilterChange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Items</SelectItem>
              <SelectItem value="documents">Documents Only</SelectItem>
              <SelectItem value="folders">Folders Only</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={fetchRecycleBin} disabled={isLoading}>
            <RefreshCcw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {selectedItemsMap.size > 0 ? (
        <div className="flex flex-col gap-3 rounded-md border bg-muted/30 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm font-medium">
            {selectedItemsMap.size} item{selectedItemsMap.size === 1 ? '' : 's'} selected
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => setShowBulkRestore(true)}
              disabled={isProcessing}
            >
              Restore Selected
            </Button>
            <Button
              variant="destructive"
              onClick={() => setShowBulkDelete(true)}
              disabled={isProcessing}
            >
              Delete Permanently
            </Button>
          </div>
        </div>
      ) : null}

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={allOnPageSelected ? true : someOnPageSelected ? "indeterminate" : false}
                  onCheckedChange={(checked) => toggleSelectAllOnPage(checked === true)}
                  aria-label="Select all on page"
                  disabled={isLoading || items.length === 0}
                />
              </TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="w-[30%]">File Name</TableHead>
              <TableHead>Office Unit</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Date Deleted</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="h-32 text-center">Loading recycle bin...</TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="h-32 text-center text-muted-foreground">Recycle bin is empty.</TableCell>
              </TableRow>
            ) : (
              items.map(item => (
                <TableRow key={getItemKey(item)} data-state={selectedItemsMap.has(getItemKey(item)) ? 'selected' : undefined}>
                  <TableCell>
                    <Checkbox
                      checked={selectedItemsMap.has(getItemKey(item))}
                      onCheckedChange={(checked) => toggleItemSelection(item, checked === true)}
                      aria-label={`Select ${item.name || item.title}`}
                    />
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="flex w-fit items-center gap-1.5 capitalize">
                      {item.type === 'folder' ? <Folder className="h-3 w-3" /> : <FileText className="h-3 w-3" />}
                      {item.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">{item.name || item.title}</TableCell>
                  <TableCell className="text-sm font-medium text-muted-foreground">{item.orgUnitName || 'Global Access'}</TableCell>
                  <TableCell
                    className="max-w-[220px] truncate text-sm text-muted-foreground"
                    title={getRecycleBinLocation(item)}
                  >
                    {getRecycleBinLocation(item)}
                  </TableCell>
                  <TableCell className="text-sm">
                    {item.deletedByFullName || "System"}
                  </TableCell>
                  <TableCell>
                    <span className="text-xs bg-muted/50 px-2 py-1 rounded-md">
                      {item.deletedByRole || item.deletedBy || 'System'}
                    </span>
                  </TableCell>
                  <TableCell>
                    {item.deletedAt ? formatManilaDateTime(item.deletedAt) : 'Unknown'}
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button variant="outline" size="sm" onClick={() => setItemToRestore(item)}>
                      Restore
                    </Button>
                    <Button variant="destructive" size="sm" onClick={() => setItemToDelete(item)}>
                      Delete
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <PaginationControls
          count={itemCount}
          currentPage={currentPage}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={handlePageSizeChange}
          disabled={isLoading}
        />
      </div>

      <AlertDialog open={!!itemToRestore} onOpenChange={(open) => !open && setItemToRestore(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore {itemToRestore?.type}?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to restore <strong>{itemToRestore?.name || itemToRestore?.title}</strong>?
              {itemToRestore?.type === 'folder' && (
                <span className="block mt-2 text-primary font-medium">
                  This will also restore all documents contained within this folder.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isProcessing}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRestore} disabled={isProcessing} className="bg-brand-green hover:bg-brand-green/90">
              {isProcessing ? "Restoring..." : "Restore"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <PermanentDeleteConfirmDialog
        open={!!itemToDelete}
        item={itemToDelete}
        isProcessing={isProcessing}
        onCancel={() => setItemToDelete(null)}
        onConfirm={handleDelete}
      />

      <BulkRestoreConfirmDialog
        open={showBulkRestore}
        documentCount={selectedDocumentCount}
        folderCount={selectedFolderCount}
        totalItems={selectedItemsMap.size}
        isProcessing={isProcessing}
        onCancel={() => setShowBulkRestore(false)}
        onConfirm={handleBulkRestore}
      />

      <BulkPermanentDeleteConfirmDialog
        open={showBulkDelete}
        items={selectedItems.map(itemToPayload)}
        isProcessing={isProcessing}
        onCancel={() => setShowBulkDelete(false)}
        onConfirm={handleBulkDelete}
      />
    </div>
  );
}
