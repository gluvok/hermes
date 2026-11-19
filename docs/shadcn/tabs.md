# Tabs

Segmented navigation controls for switching between Operator Kiosk and Developer Console.

## Usage

```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export function ConsoleSwitchTabs() {
  return (
    <Tabs defaultValue="operator" className="w-full">
      <TabsList className="grid w-[400px] grid-cols-2">
        <TabsTrigger value="operator">Operator Kiosk</TabsTrigger>
        <TabsTrigger value="developer">Developer Console</TabsTrigger>
      </TabsList>
      <TabsContent value="operator">
        {/* Operator Kiosk View */}
      </TabsContent>
      <TabsContent value="developer">
        {/* Developer Subsystems View */}
      </TabsContent>
    </Tabs>
  );
}
```

## Structure
- `Tabs`: Root state container with `defaultValue` and `onValueChange`.
- `TabsList`: Segmented track background (`bg-muted p-1 text-muted-foreground rounded-lg`).
- `TabsTrigger`: Individual tab trigger button (`data-[state=active]:bg-background`).
- `TabsContent`: Render container for active panel content.
