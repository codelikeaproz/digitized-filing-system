import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function ChatInput({ value, disabled, onChange, onSubmit }: ChatInputProps) {
  return (
    <form
      className="shrink-0 border-t border-[#D7E5D8] bg-white/95 p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="flex items-end gap-2">
        <Textarea
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask where a file is, what it contains, or find related documents..."
          className="max-h-32 min-h-[46px] resize-none rounded-lg border-[#C9DACB] bg-white"
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
        />
        <Button
          type="submit"
          disabled={disabled || !value.trim()}
          size="icon"
          className="h-11 w-11 shrink-0 rounded-lg bg-[#0A4D27] hover:bg-[#083E1D]"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      <p className="mt-3 text-center text-[10px] font-medium text-[#6F8B75]">
        Developed by Ralph C. Jumao-as, Intern Programmer, 2026
      </p>
    </form>
  );
}
