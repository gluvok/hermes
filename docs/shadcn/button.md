# Button

Touch-friendly industrial action trigger with variant styling and loading feedback.

## Usage

```tsx
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

export function ZeroScaleButton({ onZero, disabled }: { onZero: () => void; disabled?: boolean }) {
  return (
    <Button variant="default" size="lg" onClick={onZero} disabled={disabled} className="min-h-12 min-w-32">
      <RefreshCw data-icon="inline-start" className="mr-2 h-4 w-4" />
      Zero Scale
    </Button>
  );
}
```

## Variants & Sizes
- `variant`: `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`.
- `size`: `default` (h-9), `sm` (h-8), `lg` (h-10), `icon` (size-9).
- Touch target: Minimum `h-11 px-6 text-base` on Raspberry Pi touch screen kiosks.
