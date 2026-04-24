import { logAudit } from "./audit";
import { toast } from "sonner";
import { api } from "./api";

export async function deleteDocument(docId: string, title: string, userId?: string) {
  try {
    await api.delete(`/api/documents/${docId}`);
    await logAudit("DELETE_DOCUMENT", `Deleted document: ${title}`);
    toast.success("Document deleted");
  } catch (error: any) {
    console.error("Delete Error:", error);
    toast.error(error.message || "Failed to delete document");
    throw error;
  }
}
