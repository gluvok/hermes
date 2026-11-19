"use client";

import * as React from "react";
import { OperatorHUD } from "@/components/kiosk/operator-hud";
import { MaintainerSheet } from "@/components/kiosk/maintainer-sheet";
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
import { Wrench, Wifi } from "lucide-react";

export default function HermesKioskPage() {
  const [isMaintainerOpen, setIsMaintainerOpen] = React.useState(false);
  const [isOverrideOpen, setIsOverrideOpen] = React.useState(false);
  const [plateInput, setPlateInput] = React.useState("KA-01-MJ-5021");
  const [activePlate, setActivePlate] = React.useState("KA-01-MJ-5021");

  const handleSavePlate = () => {
    setActivePlate(plateInput);
    setIsOverrideOpen(false);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      {/* 56px Industrial App Bar matching Janus */}
      <header className="h-14 border-b border-border bg-card/60 backdrop-blur px-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="font-heading font-bold text-sm tracking-tight text-foreground">
              LUVOK Hermes
            </span>
            <Badge variant="outline" className="text-2xs font-mono">v2.0</Badge>
          </div>
          <div className="h-4 w-px bg-border hidden sm:block" />
          <span className="text-xs text-muted-foreground hidden sm:inline font-mono">
            Station #01 &bull; Automated Kiosk
          </span>
        </div>

        {/* Minimal Right Actions: Status & Maintainer Sheet Trigger */}
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="gap-1.5 text-xs text-emerald-400 border-emerald-500/20">
            <Wifi className="h-3 w-3" />
            <span className="hidden sm:inline">Wi-Fi Online</span>
          </Badge>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsMaintainerOpen(true)}
            className="h-8 gap-1.5 text-xs font-mono"
            title="Open Maintainer Sheet"
          >
            <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="hidden md:inline">Maintainer</span>
          </Button>
        </div>
      </header>

      {/* Main Single-View Customer Hero Canvas */}
      <main className="flex-1 p-4 lg:p-6 flex flex-col justify-center">
        <OperatorHUD
          plateNumber={activePlate}
          onOverridePlate={() => setIsOverrideOpen(true)}
          onPrint={() => window.print()}
        />
      </main>

      {/* Slide-Over Diagnostics Sheet for Maintainers */}
      <MaintainerSheet
        open={isMaintainerOpen}
        onClose={() => setIsMaintainerOpen(false)}
      />

      {/* Manual License Plate Override Modal */}
      <Dialog open={isOverrideOpen} onOpenChange={setIsOverrideOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Correct Vehicle License Plate</DialogTitle>
            <DialogDescription>
              Enter visually verified registration number if ANPR confidence is low.
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
