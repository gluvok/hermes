"use client";

import * as React from "react";
import { Monitor, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConsoleModeSwitcherProps {
  mode: "operator" | "developer";
  onModeChange: (mode: "operator" | "developer") => void;
}

export function ConsoleModeSwitcher({ mode, onModeChange }: ConsoleModeSwitcherProps) {
  return (
    <div
      role="group"
      aria-label="Console Mode Switcher"
      className="inline-flex h-9 items-center rounded-lg bg-muted/60 p-1 border border-border"
    >
      <button
        type="button"
        onClick={() => onModeChange("operator")}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-all",
          mode === "operator"
            ? "bg-background text-foreground shadow-sm font-semibold"
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        <Monitor className="h-3.5 w-3.5" />
        Operator Kiosk
      </button>
      <button
        type="button"
        onClick={() => onModeChange("developer")}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-all",
          mode === "developer"
            ? "bg-background text-foreground shadow-sm font-semibold"
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        <Terminal className="h-3.5 w-3.5" />
        Developer Console
      </button>
    </div>
  );
}
