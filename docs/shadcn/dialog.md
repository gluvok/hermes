# Dialog

Modal dialog surface for manual license plate correction, calibration override, and system reboot.

## Usage

```tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function ManualPlateDialog({ onSave }: { onSave: (plate: string) => void }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">Override Plate</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Correct Vehicle License Plate</DialogTitle>
          <DialogDescription>
            Enter verified registration number if ANPR camera confidence is below threshold.
          </DialogDescription>
        </DialogHeader>
        {/* Form controls */}
        <DialogFooter>
          <Button type="submit">Confirm & Transmit</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

## Accessibility Requirements
- Every `Dialog` must contain a `DialogTitle` (even if visually hidden using `sr-only`).
- Focus is automatically trapped inside the dialog when open and restored on dismiss.
