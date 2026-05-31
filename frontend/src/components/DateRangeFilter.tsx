import { useState } from "react";
import { format } from "date-fns";
import { Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type DateRangeFilterProps = {
  startDate: string;
  endDate: string;
  onApply: (startDate: string, endDate: string) => void;
  onClear: () => void;
  className?: string;
  startDateId?: string;
  endDateId?: string;
};

function getDateRangeLabel(startDate: string, endDate: string) {
  if (!startDate && !endDate) return "Date Range";
  const formatShortDate = (value: string) => format(new Date(`${value}T00:00:00`), "MMM d, yyyy");
  if (startDate && endDate) return `${formatShortDate(startDate)} - ${formatShortDate(endDate)}`;
  if (startDate) return `From ${formatShortDate(startDate)}`;
  return `Until ${formatShortDate(endDate)}`;
}

export function DateRangeFilter({
  startDate,
  endDate,
  onApply,
  onClear,
  className,
  startDateId = "date-range-start",
  endDateId = "date-range-end",
}: DateRangeFilterProps) {
  const [open, setOpen] = useState(false);
  const [draftStartDate, setDraftStartDate] = useState("");
  const [draftEndDate, setDraftEndDate] = useState("");

  const openDialog = () => {
    setDraftStartDate(startDate);
    setDraftEndDate(endDate);
    setOpen(true);
  };

  const applyDateRange = () => {
    onApply(draftStartDate, draftEndDate);
    setOpen(false);
  };

  const clearDateRange = () => {
    setDraftStartDate("");
    setDraftEndDate("");
    onClear();
    setOpen(false);
  };

  return (
    <>
      <Button
        type="button"
        variant={startDate || endDate ? "default" : "outline"}
        className={cn("h-9 gap-2 px-3 py-1 text-sm font-normal", className)}
        onClick={openDialog}
      >
        <Calendar className="h-4 w-4" />
        {getDateRangeLabel(startDate, endDate)}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Filter by Date Range</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor={startDateId}>Start Date</Label>
              <Input
                id={startDateId}
                type="date"
                value={draftStartDate}
                onChange={(event) => setDraftStartDate(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor={endDateId}>End Date</Label>
              <Input
                id={endDateId}
                type="date"
                value={draftEndDate}
                onChange={(event) => setDraftEndDate(event.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={clearDateRange}>
              Clear
            </Button>
            <Button type="button" onClick={applyDateRange}>
              Apply
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
