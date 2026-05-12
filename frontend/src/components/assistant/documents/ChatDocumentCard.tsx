import { Eye, FolderOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface AssistantMatchedDocument {
  id: string;
  title: string;
  code?: string;
  folderId?: string;
  folderPath?: string;
  category?: string;
  description?: string;
  keywords?: string[];
}

interface ChatDocumentCardProps {
  document: AssistantMatchedDocument;
  onView?: (document: AssistantMatchedDocument) => void;
  onOpenFolder?: (document: AssistantMatchedDocument) => void;
}

export function ChatDocumentCard({ document, onView, onOpenFolder }: ChatDocumentCardProps) {
  return (
    <div className="rounded-lg bg-white p-3 shadow-sm ring-1 ring-[#D7E5D8]">
      <div className="space-y-1">
        <p className="line-clamp-2 text-sm font-bold text-[#112217]">{document.title}</p>
        <div className="flex flex-wrap gap-1.5">
          {document.code && <Badge variant="outline" className="border-[#C9DACB] text-[#31583B]">Code {document.code}</Badge>}
          {document.category && <Badge className="bg-[#E8F1EA] text-[#0A4D27] hover:bg-[#E8F1EA]">{document.category}</Badge>}
        </div>
      </div>
      <div className="mt-2 space-y-1 text-xs leading-relaxed text-[#55735C]">
        {document.folderPath && <p><span className="font-semibold text-[#31583B]">Folder:</span> {document.folderPath}</p>}
        {document.description && <p><span className="font-semibold text-[#31583B]">Description:</span> {document.description}</p>}
        {!!document.keywords?.length && (
          <p><span className="font-semibold text-[#31583B]">Keywords:</span> {document.keywords.join(", ")}</p>
        )}
      </div>
      <div className="mt-3 flex gap-2">
        <Button type="button" size="sm" variant="outline" className="h-8 border-[#C9DACB]" onClick={() => onView?.(document)}>
          <Eye className="mr-1.5 h-3.5 w-3.5" />
          View
        </Button>
        <Button type="button" size="sm" variant="ghost" className="h-8 text-[#0A4D27]" onClick={() => onOpenFolder?.(document)}>
          <FolderOpen className="mr-1.5 h-3.5 w-3.5" />
          Open Folder
        </Button>
      </div>
    </div>
  );
}
