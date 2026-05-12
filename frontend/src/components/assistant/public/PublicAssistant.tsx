import { useState } from "react";
import { PublicAssistantDrawer } from "./PublicAssistantDrawer";
import { PublicAssistantFloatingButton } from "./PublicAssistantFloatingButton";

export function PublicAssistant() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <PublicAssistantFloatingButton onClick={() => setOpen(true)} />
      <PublicAssistantDrawer open={open} onOpenChange={setOpen} />
    </>
  );
}
