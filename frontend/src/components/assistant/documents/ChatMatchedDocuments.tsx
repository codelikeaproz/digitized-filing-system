import { AssistantMatchedDocument, ChatDocumentCard } from "./ChatDocumentCard";

interface ChatMatchedDocumentsProps {
  documents: AssistantMatchedDocument[];
  onView?: (document: AssistantMatchedDocument) => void;
  onOpenFolder?: (document: AssistantMatchedDocument) => void;
}

export function ChatMatchedDocuments({ documents, onView, onOpenFolder }: ChatMatchedDocumentsProps) {
  if (!documents.length) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#55735C]">Matched documents</p>
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
