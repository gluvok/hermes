"use client";

import * as React from "react";
import { ConsoleModeSwitcher } from "@/components/kiosk/console-mode-switcher";
import { OperatorHUD } from "@/components/kiosk/operator-hud";
import { DeveloperConsole } from "@/components/kiosk/developer-console";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, Wifi } from "lucide-react";

export default function HermesKioskPage() {
  const [mode, setMode] = React.useState<"operator" | "developer">("operator");
  const [isOverrideOpen, setIsOverrideOpen] = React.useState(false);
  const [plateInput, setPlateInput] = React.useState("KA-01-MJ-5021");
  const [activePlate, setActivePlate] = React.useState("KA-01-MJ-5021");

  const handleSavePlate = () => {
    setActivePlate(plateInput);
    setIsOverrideOpen(false);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      {/* Top Industrial App Bar */}
      <header className="h-14 border-b border-border bg-card/50 backdrop-blur px-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="font-heading font-bold text-sm tracking-tight text-foreground">
              LUVOK Hermes
            </span>
            <Badge variant="outline" className="text-2xs font-mono">v2.0-EDGE</Badge>
          </div>
          <span className="text-xs text-muted-foreground hidden sm:inline">
            Weighbridge Edge
          </span>
        </div>

        {/* Console Switcher */}
        <ConsoleModeSwitcher mode={mode} onModeChange={setMode} />

        {/* Network & Security Status */}
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="gap-1.5 text-xs text-emerald-400 border-emerald-500/20">
            <Wifi className="h-3 w-3" />
            <span className="hidden sm:inline">Wi-Fi Connected</span>
          </Badge>
          <Badge variant="secondary" className="gap-1 text-2xs font-mono">
            <ShieldCheck className="h-3 w-3" />
            Zero-Disk
          </Badge>
        </div>
      </header>

      {/* Main Kiosk Content Area */}
      <main className="flex-1 py-6">
        {mode === "operator" ? (
          <OperatorHUD
            plateNumber={activePlate}
            onOverridePlate={() => setIsOverrideOpen(true)}
            onPrint={() => window.print()}
          />
        ) : (
          <DeveloperConsole />
        )}
      </main>

      {/* Manual License Plate Override Modal */}
      <Dialog open={isOverrideOpen} onOpenChange={setIsOverrideOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Correct Vehicle License Plate</DialogTitle>
            <DialogDescription>
              Enter the visually verified registration number if the automatic camera confidence is low.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="text-xs text-muted-foreground block mb-2 font-medium">
              Registration Number
            </label>
            <input
              type="text"
              value={plateInput}
              onChange={(e) => setPlateInput(e.target.value.toUpperCase())}
              className="w-full h-11 px-3 rounded-lg border border-border bg-background font-mono text-lg font-bold tracking-wider uppercase focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g. KA01MJ5021"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsOverrideOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSavePlate}>
              Confirm Plate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
