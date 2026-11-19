# Sheet

Slide-over sheet panel extending from the screen edge, providing dedicated maintainer diagnostics without occluding or navigating away from the customer/client dashboard.

## Usage

```tsx
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Wrench } from "lucide-react";

export function MaintainerSheetTrigger() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5 font-mono text-xs">
          <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
          <span>Maintainer</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full sm:max-w-md bg-card border-l border-border p-6">
        <SheetHeader>
          <SheetTitle>Hardware & Subsystem Diagnostics</SheetTitle>
          <SheetDescription>
            Tuning controls for Scale UART, optical crop margins, and Wi-Fi failover.
          </SheetDescription>
        </SheetHeader>
        {/* Tabbed diagnostic cards */}
        <SheetFooter className="mt-6 border-t border-border pt-4">
          <span className="text-2xs text-muted-foreground font-mono">Zero-Disk Mode Active</span>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
```

## Structure & Accessibility
- `Sheet`: Root primitive managing open/closed state.
- `SheetContent`: Slide-out container supporting `side="right" | "left" | "top" | "bottom"`. In Hermes, always positioned on the right (`side="right"`).
- `SheetHeader` & `SheetTitle`: Accessible title declaration (required for screen reader compliance).
- Focus is automatically trapped when open, and pressing `Escape` dismisses the sheet.
