# Card

Container surface for grouping telemetry widgets, live weight displays, and system health status.

## Usage

```tsx
import {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

export function LiveWeightCard({ weight, unit }: { weight: number; unit: string }) {
  return (
    <Card className="border-border bg-card text-card-foreground">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">Scale Indicator</CardTitle>
        <CardDescription>/dev/ttyAMA0 @ 1200 baud</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="text-4xl font-bold font-mono tracking-tight">
          {weight.toFixed(2)} <span className="text-lg font-normal text-muted-foreground">{unit}</span>
        </div>
      </CardContent>
      <CardFooter className="text-xs text-muted-foreground">
        Hardware filter: 10s stability debounce
      </CardFooter>
    </Card>
  );
}
```

## Props & Composition
- `Card`: Root container with `rounded-xl border bg-card text-card-foreground shadow`.
- `CardHeader`: Flex container for title and description with default padding.
- `CardTitle`: Semantic heading styled with tight letter-spacing.
- `CardDescription`: Muted secondary text.
- `CardContent`: Primary content area.
- `CardFooter`: Footer actions and metadata.
