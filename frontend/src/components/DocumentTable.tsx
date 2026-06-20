/**
 * DocumentTable — document list with preview, rename, delete (role-dependent).
 * Used by DocumentsPage. APIs: PATCH rename, DELETE document, file_url preview.
 */
import * as React from 'react';
import { cn } from '@/lib/utils';
import { getRequisitionerTableCell, getTitleTooltipRequisitioners } from '@/lib/requisitioner';
import { Eye, Download, MoreVertical, FileText, Trash2, Pencil, FilePenLine } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from '@/lib/auth-context';
import { formatDocumentTableDate } from '@/lib/time';
import { isGoogleDriveOnlyDocument } from '@/lib/document-actions';

interface DocumentTableProps {
  data: any[];
  onView?: (doc: any) => void;
  onDownload?: (doc: any) => void;
  onRename?: (doc: any, fileName: string) => Promise<void> | void;
  onEdit?: (doc: any) => void;
  onDelete?: (doc: any) => void;
}

export function DocumentTable({ data, onView, onDownload, onRename, onEdit, onDelete }: DocumentTableProps) {
  const { user } = useAuth();
  const canDelete = user?.role?.toLowerCase() !== 'staff';
  const canEdit = user?.role?.toLowerCase() === 'admin' || user?.role?.toLowerCase() === 'dept_head';

  const [docToDelete, setDocToDelete] = React.useState<any>(null);
  const [docToRename, setDocToRename] = React.useState<any>(null);
  const [renameValue, setRenameValue] = React.useState("");
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [isRenaming, setIsRenaming] = React.useState(false);

  const openRename = (doc: any) => {
    const currentName = doc.title || doc.file_name || "";
    setDocToRename(doc);
    setRenameValue(currentName.replace(/\.pdf$/i, ""));
  };

  return (
    <div className="min-w-0 overflow-hidden rounded-md border bg-card">
      <Table className="min-w-[900px]">
        <TableHeader>
          <TableRow>
            <TableHead className="w-[25%]">Title</TableHead>
            <TableHead>Requisitioner</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Location</TableHead>
            <TableHead>Date</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                No documents found.
              </TableCell>
            </TableRow>
          ) : (
            data.map((doc) => {
              const requisitionerCell = getRequisitionerTableCell(doc);
              const requisitionersTooltip = getTitleTooltipRequisitioners(doc);
              return (
              <TableRow key={doc.id}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <TooltipProvider delay={200}>
                      <Tooltip>
                        <TooltipTrigger className="truncate max-w-[250px] cursor-help hover:text-brand-green transition-colors font-medium border-0 bg-transparent p-0 text-left">
                          {doc.title}
                        </TooltipTrigger>
                        <TooltipContent side="right" className="max-w-[340px] p-3 text-xs shadow-xl bg-card text-card-foreground border">
                           <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-start">
                             <div className="shrink-0 text-muted-foreground font-medium">Code:</div>
                             <div className="min-w-0 font-mono break-all">{doc.code || "—"}</div>

                             <div className="shrink-0 text-muted-foreground font-medium">Description:</div>
                             <div className="min-w-0 break-words">{doc.description || "—"}</div>

                             <div className="shrink-0 text-muted-foreground font-medium">Keywords:</div>
                             <div className="min-w-0 break-words">
                               {Array.isArray(doc.keywords) && doc.keywords.length > 0 ? doc.keywords.join(", ") : "—"}
                             </div>

                             <div className="shrink-0 text-muted-foreground font-medium">Requisitioners:</div>
                             <div className="min-w-0 whitespace-pre-line break-words leading-relaxed">
                               {requisitionersTooltip || "—"}
                             </div>
                           </div>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </TableCell>
                <TableCell className="max-w-[180px] truncate">
                  <span className="block truncate">{requisitionerCell.label || "—"}</span>
                </TableCell>
                <TableCell className="max-w-[160px] truncate">{doc.category}</TableCell>
                <TableCell className="text-xs text-muted-foreground font-mono truncate max-w-[150px]">
                  {doc.filePath}
                </TableCell>
                <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                  {formatDocumentTableDate(doc.createdAt || doc.created_at)}
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      className={cn(
                        buttonVariants({ variant: "ghost" }),
                        "h-8 w-8 p-0"
                      )}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => onView?.(doc)}>
                        <Eye className="mr-2 h-4 w-4 text-blue-600" />
                        View
                      </DropdownMenuItem>
                      {!isGoogleDriveOnlyDocument(doc) && (
                        <DropdownMenuItem onClick={() => onDownload?.(doc)}>
                          <Download className="mr-2 h-4 w-4 text-green-600" />
                          Download
                        </DropdownMenuItem>
                      )}
                      {canEdit && (
                        <DropdownMenuItem onClick={() => onEdit?.(doc)}>
                          <FilePenLine className="mr-2 h-4 w-4 text-blue-600" />
                          Edit Details
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuItem onClick={() => openRename(doc)}>
                        <Pencil className="mr-2 h-4 w-4 text-amber-600" />
                        Rename
                      </DropdownMenuItem>

                      {canDelete && (
                        <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={() => setDocToDelete(doc)}>
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            );
            })
          )}
        </TableBody>
      </Table>

      {/* Delete Confirmation Modal */}
      <AlertDialog open={!!docToDelete} onOpenChange={(open) => !open && !isDeleting && setDocToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Document</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this item?
              <br />
              <span className="font-semibold text-foreground mt-2 block">
                {docToDelete?.title}
              </span>
              <span className="block mt-2 text-muted-foreground italic">
                The document will be moved to the recycle bin.
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={async (e) => {
                e.preventDefault();
                setIsDeleting(true);
                try {
                  if (onDelete && docToDelete) {
                    await onDelete(docToDelete);
                  }
                  setDocToDelete(null);
                } finally {
                  setIsDeleting(false);
                }
              }}
              className="bg-red-600 text-white hover:bg-red-700"
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={!!docToRename} onOpenChange={(open) => !open && !isRenaming && setDocToRename(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Document</DialogTitle>
            <DialogDescription>
              Edit the base file name. The PDF extension is locked.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <label htmlFor="document-file-name" className="text-sm font-medium">
              File name
            </label>
            <div className="flex">
              <Input
                id="document-file-name"
                value={renameValue}
                onChange={(event) => setRenameValue(event.target.value)}
                disabled={isRenaming}
                className="rounded-r-none"
                placeholder="Sample RRL"
                autoFocus
              />
              <div className="flex items-center rounded-r-md border border-l-0 bg-muted px-3 text-sm font-medium text-muted-foreground">
                .pdf
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDocToRename(null)} disabled={isRenaming}>
              Cancel
            </Button>
            <Button
              onClick={async () => {
                if (!docToRename || !renameValue.trim()) return;
                setIsRenaming(true);
                try {
                  await onRename?.(docToRename, renameValue.trim());
                  setDocToRename(null);
                } finally {
                  setIsRenaming(false);
                }
              }}
              disabled={isRenaming || !renameValue.trim()}
            >
              {isRenaming ? "Saving..." : "Save Rename"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
