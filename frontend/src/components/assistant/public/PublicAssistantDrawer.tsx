import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { PublicChatTypingState } from "./PublicChatTypingState";

type Message = {
  id: number;
  role: PublicAssistantMessageRole;
  content: string;
};

const PUBLIC_CHAT_MIN_LENGTH = 2;
const PUBLIC_CHAT_COOLDOWN_MS = 1200;
const PUBLIC_CHAT_TYPING_MS = 500;
const PUBLIC_CHAT_MAX_USER_MESSAGES = 40;
const PUBLIC_CHAT_DUPLICATE_WINDOW_MS = 30_000;

const SHORT_GREETING_ALLOWLIST = new Set(["hi", "hey", "ok"]);

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

const GREETING_PATTERN =
  /^(hi|hello|hey|good morning|good afternoon|good evening)(?:[!?.…,;:]+)?$/i;

const HELP_PATTERN = /^(help|what can you do|what do you do|how can you help(?: me)?)(?:[!?.…,;:]+)?$/i;

function normalizePublicQuery(query: string) {
  return query.trim().toLowerCase();
}

function publicAnswerFor(query: string) {
  const normalized = normalizePublicQuery(query);

  if (GREETING_PATTERN.test(normalized)) {
    return "Hey! Glad you're here. Ask me anything about how DFS works — uploads, folders, roles, or signing in.";
  }

  if (HELP_PATTERN.test(normalized)) {
    return (
      "I can walk you through the basics — what DFS is, how to upload a PDF after you log in, " +
      "what the different roles mean, and how to get into your account.\n\n" +
      "If you need to search or open actual documents, you'll need to log in first."
    );
  }

  if (DEVELOPMENT_PATTERNS.some((pattern) => normalized.includes(pattern))) {
    return "DFS was built by Ralph C. Jumao-as, Intern Programmer (2026), under the Software Development Department at CISC College of Information Sciences and Computing.";
  }

  if (RESTRICTED_PATTERNS.some((pattern) => normalized.includes(pattern))) {
    return "I can't look up files or folders from here — you'll need to log in first. After that, the Document Assistant can help you find what you need.";
  }

  if (normalized.includes("upload")) {
    return "After you log in, open Documents and click Upload. Choose where the file should go, pick a category, fill in a few details, and save — that's it.";
  }

  if (normalized.includes("structur") || normalized.includes("organiz") || normalized.includes("categor")) {
    return "Picture a filing cabinet, but digital. Files live in folders under your office or department, each tagged with a category and a short description so people can search and pull them up later.";
  }

  if (normalized.includes("role")) {
    return "There are three roles: Admin keeps the whole system running, Head oversees their team's files, and Staff handles everyday uploads and filing within their office unit.";
  }

  if (normalized.includes("log in") || normalized.includes("login")) {
    return "Use the email and password your administrator set up for you. If you're locked out or just got your account, reach out to your DFS admin.";
  }

  if (
    normalized.includes("how it work") ||
    normalized.includes("how does it work") ||
    normalized.includes("how dfs work") ||
    normalized.includes("how does dfs work")
  ) {
    return "Pretty simple, really — your office uploads PDFs, sorts them into folders, and finds them again when needed. Each person only sees what their role allows, so records stay in the right hands.";
  }

  if (
    normalized.includes("what is") &&
    (normalized.includes("dfs") ||
      normalized.includes("digitized") ||
      normalized.includes("filing system"))
  ) {
    return "DFS — the Digitized Filing System — is where your office stores and organizes PDF records online. Instead of paper cabinets, everything lives in folders you can search and share safely within your team.";
  }

  return "DFS helps your office keep PDF records in one place — upload them, file them in the right folder, and find them again whenever you need. Access depends on your role, so people only see what's meant for them.";
}

function createInitialMessages(): Message[] {
  return [
    {
      id: 1,
      role: "assistant",
      content: "Hi! I'm the DFS Assistant — here to help if you're new and want to know how the system works.",
    },
  ];
}

interface PublicAssistantDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PublicAssistantDrawer({ open, onOpenChange }: PublicAssistantDrawerProps) {
  const initialMessages = useMemo(() => createInitialMessages(), []);
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [value, setValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isCooldown, setIsCooldown] = useState(false);
  const [inputHint, setInputHint] = useState("");
  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const lastQueryRef = useRef("");
  const lastQueryAtRef = useRef(0);
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cooldownTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const userMessageCount = useMemo(
    () => messages.filter((message) => message.role === "user").length,
    [messages]
  );
  const sessionLimitReached = userMessageCount >= PUBLIC_CHAT_MAX_USER_MESSAGES;
  const inputLocked = isTyping || isCooldown || sessionLimitReached;

  const clearTimers = useCallback(() => {
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
    if (cooldownTimeoutRef.current) {
      clearTimeout(cooldownTimeoutRef.current);
      cooldownTimeoutRef.current = null;
    }
  }, []);

  const resetSession = useCallback(() => {
    clearTimers();
    setMessages(createInitialMessages());
    setValue("");
    setIsTyping(false);
    setIsCooldown(false);
    setInputHint("");
    lastQueryRef.current = "";
    lastQueryAtRef.current = 0;
  }, [clearTimers]);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, isTyping]);

  useEffect(() => {
    if (!open) {
      resetSession();
    }
  }, [open, resetSession]);

  useEffect(() => clearTimers, [clearTimers]);

  const startCooldown = useCallback(() => {
    setIsCooldown(true);
    cooldownTimeoutRef.current = setTimeout(() => {
      setIsCooldown(false);
      cooldownTimeoutRef.current = null;
    }, PUBLIC_CHAT_COOLDOWN_MS);
  }, []);

  const submitQuestion = useCallback(
    (question: string) => {
      if (inputLocked) return;

      const trimmed = question.trim();
      if (!trimmed) return;

      if (sessionLimitReached) {
        setInputHint("Message limit reached. Close and reopen the assistant to continue.");
        return;
      }

      const normalized = normalizePublicQuery(trimmed);
      const isShortAllowed = SHORT_GREETING_ALLOWLIST.has(normalized);
      if (trimmed.length < PUBLIC_CHAT_MIN_LENGTH && !isShortAllowed) {
        setInputHint(`Please enter at least ${PUBLIC_CHAT_MIN_LENGTH} characters.`);
        return;
      }

      setInputHint("");

      const now = Date.now();
      const isDuplicate =
        normalized === lastQueryRef.current &&
        now - lastQueryAtRef.current < PUBLIC_CHAT_DUPLICATE_WINDOW_MS;

      const answer = isDuplicate
        ? "Looks like you already asked that — try one of the suggested questions, or ask about uploads, roles, or logging in."
        : publicAnswerFor(trimmed);

      lastQueryRef.current = normalized;
      lastQueryAtRef.current = now;

      setMessages((current) => [...current, { id: now, role: "user", content: trimmed }]);
      setValue("");
      setIsTyping(true);

      typingTimeoutRef.current = setTimeout(() => {
        setMessages((current) => [
          ...current,
          { id: now + 1, role: "assistant", content: answer },
        ]);
        setIsTyping(false);
        typingTimeoutRef.current = null;
        startCooldown();
      }, PUBLIC_CHAT_TYPING_MS);
    },
    [inputLocked, sessionLimitReached, startCooldown]
  );

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
              I can explain how DFS works, but I can't access your files until you log in.
            </div>
            {messages.length === 1 && !inputLocked && (
              <PublicAssistantPromptList disabled={inputLocked} onSelect={submitQuestion} />
            )}
            <div className="space-y-3">
              {messages.map((message) => (
                <PublicAssistantMessage key={message.id} role={message.role}>
                  {message.content}
                </PublicAssistantMessage>
              ))}
              {isTyping && <PublicChatTypingState />}
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
                disabled={inputLocked}
                onChange={(event) => {
                  setValue(event.target.value);
                  if (inputHint) setInputHint("");
                }}
                placeholder={
                  sessionLimitReached
                    ? "Message limit reached"
                    : isTyping
                      ? "Assistant is typing..."
                      : isCooldown
                        ? "Please wait a moment..."
                        : "Ask about DFS basics..."
                }
                className="h-10 rounded-lg border-[#C9DACB] bg-white"
              />
              <Button
                type="submit"
                size="icon"
                disabled={inputLocked || !value.trim()}
                className="h-10 w-10 rounded-lg bg-[#0A4D27] hover:bg-[#083E1D]"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            {(inputHint || sessionLimitReached) && (
              <p className="mt-2 text-center text-[10px] font-medium text-[#8B5E3C]">
                {sessionLimitReached
                  ? "Message limit reached. Close and reopen the assistant to continue."
                  : inputHint}
              </p>
            )}
            <p className="mt-3 text-center text-[10px] font-medium text-[#6F8B75]">
              Developed by Ralph C. Jumao-as, Intern Programmer, 2026
            </p>
          </form>
        </div>
      </SheetContent>
    </Sheet>
  );
}
