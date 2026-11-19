"use client";

import * as React from "react";
import { X, Cpu, Camera, Cloud, Wifi, Activity, Settings, Terminal, ShieldCheck } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

interface MaintainerSheetProps {
  open: boolean;
  onClose: () => void;
}

export function MaintainerSheet({ open, onClose }: MaintainerSheetProps) {
  const [cropMargin, setCropMargin] = React.useState([45]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop Overlay */}
      <div
        className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Slide-Over Right Panel */}
      <aside className="fixed top-0 right-0 bottom-0 z-50 w-full max-w-md bg-card border-l border-border shadow-2xl flex flex-col transition-transform animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-card/90 backdrop-blur">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-foreground">Maintainer Diagnostics</h2>
              <p className="text-2xs text-muted-foreground font-mono">Hardware & System Tuning</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content Tabs */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <Tabs defaultValue="scale" className="w-full">
            <TabsList className="grid grid-cols-3 gap-1 h-auto p-1 bg-muted/60 mb-4">
              <TabsTrigger value="scale" className="text-2xs py-1.5 flex items-center gap-1">
                <Cpu className="h-3 w-3" /> Scale
              </TabsTrigger>
              <TabsTrigger value="crop" className="text-2xs py-1.5 flex items-center gap-1">
                <Camera className="h-3 w-3" /> Crop
              </TabsTrigger>
              <TabsTrigger value="network" className="text-2xs py-1.5 flex items-center gap-1">
                <Wifi className="h-3 w-3" /> Wi-Fi
              </TabsTrigger>
            </TabsList>

            <TabsContent value="scale" className="space-y-3">
              <Card>
                <CardHeader className="p-3 pb-1">
                  <CardTitle className="text-xs">UART Serial Stream</CardTitle>
                  <CardDescription className="text-2xs">/dev/ttyAMA0 @ 1200 baud</CardDescription>
                </CardHeader>
                <CardContent className="p-3 pt-2 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Port:</span>
                    <span className="font-mono">/dev/ttyAMA0</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Baud:</span>
                    <span className="font-mono">1200 bps</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Drain Trap:</span>
                    <Badge variant="emerald" className="text-2xs">ARMED 30s</Badge>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="crop" className="space-y-3">
              <Card>
                <CardHeader className="p-3 pb-1">
                  <CardTitle className="text-xs">Optical Crop Tuning</CardTitle>
                  <CardDescription className="text-2xs">Margin expansion for plate OCR</CardDescription>
                </CardHeader>
                <CardContent className="p-3 pt-2 space-y-3">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Expansion Margin:</span>
                    <span className="font-mono font-semibold">{cropMargin[0]}%</span>
                  </div>
                  <Slider value={cropMargin} onValueChange={setCropMargin} min={10} max={100} step={1} />
                  <Button size="sm" variant="outline" className="w-full text-xs h-8">
                    Persist Crop Parameters
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="network" className="space-y-3">
              <Card>
                <CardHeader className="p-3 pb-1">
                  <CardTitle className="text-xs">Local Edge Network</CardTitle>
                  <CardDescription className="text-2xs">nmcli Hotspot & Station Status</CardDescription>
                </CardHeader>
                <CardContent className="p-3 pt-2 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <Badge variant="emerald" className="text-2xs">Wi-Fi Online</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">SSID:</span>
                    <span className="font-mono">Plant_Industrial</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Emergency AP:</span>
                    <span className="font-mono text-amber-400">Standby (hermes)</span>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-card/80 flex items-center justify-between text-2xs text-muted-foreground font-mono">
          <span>Zero-Disk &bull; In-RAM</span>
          <Button variant="outline" size="sm" onClick={onClose} className="h-7 text-xs">
            Close Sheet
          </Button>
        </div>
      </aside>
    </>
  );
}
