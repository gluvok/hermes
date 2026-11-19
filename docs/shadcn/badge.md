# Badge

Visual status pill indicating hardware connection states, stability markers, and network telemetry.

## Usage

```tsx
import { Badge } from "@/components/ui/badge";

export function StabilityBadge({ isStable }: { isStable: boolean }) {
  if (isStable) {
    return <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 bg-emerald-500/10">STABLE</Badge>;
  }
  return <Badge variant="secondary" className="animate-pulse">SAMPLING</Badge>;
}
```

## Variants
- `default`: High contrast primary action indicator.
- `secondary`: Muted status tag (e.g. `OFFLINE`, `IDLE`).
- `destructive`: Error state (e.g. `SERIAL_DISCONNECTED`, `AUTH_ERROR`).
- `outline`: Bordered indicator for low-emphasis metrics.
