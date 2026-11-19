# Slider

Precision slider for calibrating weighbridge stability thresholds and sensor timeouts.

## Usage

```tsx
import { Slider } from "@/components/ui/slider";

export function StabilityWindowSlider({
  value,
  onChange,
}: {
  value: number;
  onChange: (val: number[]) => void;
}) {
  return (
    <div className="space-y-2">
      <span className="text-sm font-medium">Stability Window: {value}s</span>
      <Slider
        defaultValue={[value]}
        max={30}
        min={1}
        step={1}
        onValueChange={onChange}
        className="w-full"
      />
    </div>
  );
}
```

## Props
- `defaultValue`: Initial array of slider values.
- `min`: Minimum numeric value (e.g. 1 second).
- `max`: Maximum numeric value (e.g. 30 seconds).
- `step`: Step granularity.
- `onValueChange`: Callback triggered on drag/keyboard events.
