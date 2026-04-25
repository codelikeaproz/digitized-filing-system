import React, { useState, useEffect } from 'react';
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
import { FileText, Folder, RefreshCcw, Trash2, Trash } from 'lucide-react';
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
import { logAudit } from '@/lib/audit';
import { PaginationControls } from '@/components/PaginationControls';
import { formatManilaDateTime } from '@/lib/time';

interface RecycleBinItem {
  id: string;
  type: 'document' | 'folder';
  name?: string;
  title?: string;
  deletedAt?: string;
  deletedBy?: string;
  deletedByFullName?: string;
  deletedByRole?: string;
  orgUnitName?: string;
}

export default function RecycleBinPage() {
  const [items, setItems] = useState<RecycleBinItem[]>([]);
  const [itemCount, setItemCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'documents' | 'folders'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  
  const [itemToRestore, setItemToRestore] = useState<RecycleBinItem | null>(null);
  const [itemToDelete, setItemToDelete] = useState<RecycleBinItem | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

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

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setCurrentPage(1);
  };

  const handleFilterChange = (value: 'all' | 'documents' | 'folders' | null) => {
    if (!value) return;
    setFilter(value);
    setCurrentPage(1);
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
      await logAudit('RESTORE', `Restored ${itemToRestore.type}: ${itemToRestore.name || itemToRestore.title}`);
      await fetchRecycleBin();
    } catch (error: any) {
      toast.error(error.message || 'Failed to restore item');
    } finally {
      setIsProcessing(false);
      setItemToRestore(null);
    }
  };

  const handleDelete = async () => {
    if (!itemToDelete) return;
    setIsProcessing(true);
    try {
      await api.delete(`/api/recycle-bin/delete?type=${itemToDelete.type}&id=${itemToDelete.id}`);
      toast.success(`${itemToDelete.type === 'folder' ? 'Folder' : 'Document'} permanently deleted`);
      await logAudit('PERMANENT_DELETE', `Permanently deleted ${itemToDelete.type}: ${itemToDelete.name || itemToDelete.title}`);
      await fetchRecycleBin();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete item permanently');
    } finally {
      setIsProcessing(false);
      setItemToDelete(null);
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

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead className="w-[30%]">File Name</TableHead>
              <TableHead>Org Unit</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Date Deleted</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center">Loading recycle bin...</TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">Recycle bin is empty.</TableCell>
              </TableRow>
            ) : (
              items.map(item => (
                <TableRow key={`${item.type}-${item.id}`}>
                  <TableCell>
                    <Badge variant="outline" className="flex w-fit items-center gap-1.5 capitalize">
                      {item.type === 'folder' ? <Folder className="h-3 w-3" /> : <FileText className="h-3 w-3" />}
                      {item.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">{item.name || item.title}</TableCell>
                  <TableCell className="text-sm font-medium text-muted-foreground">{item.orgUnitName || 'Global Access'}</TableCell>
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

      <AlertDialog open={!!itemToDelete} onOpenChange={(open) => !open && setItemToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-destructive flex items-center gap-2">
              <Trash2 className="h-5 w-5" />
              Permanently Delete?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to permanently delete <strong>{itemToDelete?.name || itemToDelete?.title}</strong>?
              <span className="block mt-2 text-destructive font-bold">
                This action cannot be undone. Files will be permanently removed from storage.
              </span>
              {itemToDelete?.type === 'folder' && (
                <span className="block mt-2 font-medium">
                  All documents inside this folder will also be permanently deleted!
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isProcessing}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={isProcessing} className="bg-red-600 hover:bg-red-700 text-white hover:text-white focus:ring-red-600">
              {isProcessing ? "Deleting..." : "Delete Permanently"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
