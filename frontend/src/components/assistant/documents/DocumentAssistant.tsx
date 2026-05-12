import { useState } from "react";
import { DocumentAssistantDrawer } from "./DocumentAssistantDrawer";
import { DocumentAssistantFloatingButton } from "./DocumentAssistantFloatingButton";
import { AssistantMatchedDocument } from "./ChatDocumentCard";

interface DocumentAssistantProps {
  onViewDocument?: (document: AssistantMatchedDocument) => void;
  onOpenFolder?: (document: AssistantMatchedDocument) => void;
}

export function DocumentAssistant({ onViewDocument, onOpenFolder }: DocumentAssistantProps) {
  const [open, setOpen] = useState(false);

  const handleViewDocument = (document: AssistantMatchedDocument) => {
    onViewDocument?.(document);
    setOpen(false);
  };

  const handleOpenFolder = (document: AssistantMatchedDocument) => {
    onOpenFolder?.(document);
    setOpen(false);
  };

  return (
    <>
      <DocumentAssistantFloatingButton onClick={() => setOpen(true)} />
      <DocumentAssistantDrawer
        open={open}
        onOpenChange={setOpen}
        onViewDocument={handleViewDocument}
        onOpenFolder={handleOpenFolder}
      />
    </>
  );
}
