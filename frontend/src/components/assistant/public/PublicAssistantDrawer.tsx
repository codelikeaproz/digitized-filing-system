import React, { useEffect, useMemo, useRef, useState } from "react";
import { Bot, Send, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { PublicAssistantMessage, PublicAssistantMessageRole } from "./PublicAssistantMessage";
import { PublicAssistantPromptList } from "./PublicAssistantPromptList";

type Message = {
  id: number;
  role: PublicAssistantMessageRole;
  content: string;
};

const RESTRICTED_PATTERNS = [
  "file",
  "document",
  "folder",
  "path",
  "where is",
  "content",
  "record",
  "stored",
  "department file",
];

const DEVELOPMENT_PATTERNS = [
  "develop",
  "developed",
  "developer",
  "created",
  "made",
  "built",
  "programmer",
  "who made",
  "who build",
  "who built",
];

function publicAnswerFor(query: string) {
  const normalized = query.toLowerCase();
  if (DEVELOPMENT_PATTERNS.some((pattern) => normalized.includes(pattern))) {
    return "The Digitized Filing System was developed by Ralph C. Jumao-as, Intern Programmer, 2026, under the Department of Software Development Department, CISC College of Information Sciences and Computing.";
  }
  if (RESTRICTED_PATTERNS.some((pattern) => normalized.includes(pattern))) {
    return "Please log in to access document-related assistance.";
  }
  if (normalized.includes("upload")) {
    return "DFS accepts PDF uploads through the Documents area after login. Users select a target folder, category, document code, requisitioner name, description, and keywords before saving.";
  }
  if (normalized.includes("scan")) {
    return "Scanning uses Epson Scan 2 to create a PDF, then the local Scanner Bridge uploads that PDF into DFS when configured by the office.";
  }
  if (normalized.includes("role")) {
    return "DFS uses role-based access: Admin manages the system, Department Head oversees their OrgUnit scope, and Staff manage documents within their allowed department.";
  }
  if (normalized.includes("log in") || normalized.includes("login")) {
    return "Use the email and password issued by your administrator. If your account is new or locked, contact the DFS administrator.";
  }
  return "The Digitized Filing System helps offices organize PDF records by department, folder, category, code, description, and keywords while preserving access controls.";
}

interface PublicAssistantDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PublicAssistantDrawer({ open, onOpenChange }: PublicAssistantDrawerProps) {
  const initialMessages = useMemo<Message[]>(
    () => [
      {
        id: 1,
        role: "assistant",
        content: "Hi, I can help you understand how the Digitized Filing System works.",
      },
    ],
    []
  );
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [value, setValue] = useState("");
  const conversationEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const submitQuestion = (question: string) => {
    const trimmed = question.trim();
    if (!trimmed) return;
    setMessages((current) => [
      ...current,
      { id: Date.now(), role: "user", content: trimmed },
      { id: Date.now() + 1, role: "assistant", content: publicAnswerFor(trimmed) },
    ]);
    setValue("");
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="h-dvh max-h-dvh w-[calc(100%-0.5rem)] max-w-[460px] gap-0 overflow-hidden rounded-l-2xl border-l border-[#D7E5D8] bg-[#F7FAF6] p-0 sm:max-w-[440px] lg:max-w-[460px]">
        <SheetHeader className="shrink-0 border-b border-[#D7E5D8] bg-white/85 px-5 py-4 sm:px-6">
          <div className="flex min-w-0 items-start gap-3 pr-14">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#0A4D27] text-white">
              <Bot className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <SheetTitle className="text-base font-bold text-[#112217]">DFS Assistant</SheetTitle>
              <SheetDescription className="text-xs leading-relaxed text-[#55735C]">
                Public onboarding help only. Document assistance requires login.
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain px-5 py-4 sm:px-6">
            <div className="rounded-lg bg-[#E8F1EA] px-3 py-2 text-xs leading-relaxed text-[#31583B]">
              <ShieldCheck className="mr-1.5 inline h-3.5 w-3.5" />
              This public assistant cannot access files, folders, users, or internal records.
            </div>
            {messages.length === 1 && <PublicAssistantPromptList onSelect={submitQuestion} />}
            <div className="space-y-3">
              {messages.map((message) => (
                <PublicAssistantMessage key={message.id} role={message.role}>
                  {message.content}
                </PublicAssistantMessage>
              ))}
              <div ref={conversationEndRef} />
            </div>
          </div>

          <form
            className="shrink-0 border-t border-[#D7E5D8] bg-white/90 p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]"
            onSubmit={(event) => {
              event.preventDefault();
              submitQuestion(value);
            }}
          >
            <div className="flex gap-2">
              <Input
                value={value}
                onChange={(event) => setValue(event.target.value)}
                placeholder="Ask about DFS basics..."
                className="h-10 rounded-lg border-[#C9DACB] bg-white"
              />
              <Button type="submit" size="icon" className="h-10 w-10 rounded-lg bg-[#0A4D27] hover:bg-[#083E1D]">
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="mt-3 text-center text-[10px] font-medium text-[#6F8B75]">
              Developed by Ralph C. Jumao-as, Intern Programmer, 2026
            </p>
          </form>
        </div>
      </SheetContent>
    </Sheet>
  );
}
