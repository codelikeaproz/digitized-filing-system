import { useState } from "react";
import { DocumentAssistantDrawer } from "./DocumentAssistantDrawer";
import { DocumentAssistantFloatingButton } from "./DocumentAssistantFloatingButton";
import { AssistantMatchedDocument } from "./ChatDocumentCard";
import { AssistantPageContext } from "@/lib/assistant/pageContext";

interface DocumentAssistantProps {
  pageContext?: AssistantPageContext | null;
  onViewDocument?: (document: AssistantMatchedDocument) => void;
  onOpenFolder?: (document: AssistantMatchedDocument) => void;
}

export function DocumentAssistant({
  pageContext,
  onViewDocument,
  onOpenFolder,
}: DocumentAssistantProps) {
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
        pageContext={pageContext}
        onViewDocument={handleViewDocument}
        onOpenFolder={handleOpenFolder}
      />
    </>
  );
}
