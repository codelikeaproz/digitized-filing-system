import { AssistantMatchedDocument, ChatDocumentCard } from "./ChatDocumentCard";

interface ChatMatchedDocumentsProps {
  documents: AssistantMatchedDocument[];
  totalMatched?: number | null;
  shownCount?: number | null;
  onView?: (document: AssistantMatchedDocument) => void;
  onOpenFolder?: (document: AssistantMatchedDocument) => void;
}

export function ChatMatchedDocuments({
  documents,
  totalMatched,
  shownCount,
  onView,
  onOpenFolder,
}: ChatMatchedDocumentsProps) {
  if (!documents.length) return null;

  const shown = shownCount ?? documents.length;
  const total = totalMatched ?? documents.length;
  const label =
    total > shown
      ? `Matched documents (showing ${shown} of ${total})`
      : "Matched documents";

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#55735C]">{label}</p>
      <div className="space-y-2">
        {documents.map((document) => (
          <ChatDocumentCard
            key={document.id}
            document={document}
            onView={onView}
            onOpenFolder={onOpenFolder}
          />
        ))}
      </div>
    </div>
  );
}
