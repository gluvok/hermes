"use client";

import * as React from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Terminal, Cpu, Camera, Cloud, Wifi, Activity, Settings } from "lucide-react";

export function DeveloperConsole() {
  const [cropThreshold, setCropThreshold] = React.useState([45]);

  return (
    <div className="w-full max-w-7xl mx-auto p-4 space-y-6">
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-foreground flex items-center gap-2">
            <Terminal className="h-5 w-5 text-primary" />
            Hermes Developer Subsystem Console
          </h2>
          <p className="text-xs text-muted-foreground">
            Edge subsystem diagnostics, UART hardware buffers, and telemetry inspection.
          </p>
        </div>
        <Badge variant="outline" className="font-mono text-2xs">KERNEL 6.6-ARM64</Badge>
      </div>

      <Tabs defaultValue="scale" className="w-full">
        <TabsList className="grid w-full grid-cols-2 md:grid-cols-6 h-auto p-1 bg-muted/70">
          <TabsTrigger value="scale" className="flex items-center gap-1.5 py-2">
            <Cpu className="h-3.5 w-3.5" /> Scale UART
          </TabsTrigger>
          <TabsTrigger value="cameras" className="flex items-center gap-1.5 py-2">
            <Camera className="h-3.5 w-3.5" /> Cameras & Crop
          </TabsTrigger>
          <TabsTrigger value="cloud" className="flex items-center gap-1.5 py-2">
            <Cloud className="h-3.5 w-3.5" /> Cloud Sync
          </TabsTrigger>
          <TabsTrigger value="wifi" className="flex items-center gap-1.5 py-2">
            <Wifi className="h-3.5 w-3.5" /> Wi-Fi Network
          </TabsTrigger>
          <TabsTrigger value="telemetry" className="flex items-center gap-1.5 py-2">
            <Activity className="h-3.5 w-3.5" /> Telemetry
          </TabsTrigger>
          <TabsTrigger value="config" className="flex items-center gap-1.5 py-2">
            <Settings className="h-3.5 w-3.5" /> Config
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Scale UART */}
        <TabsContent value="scale" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">UART Serial Hardware Status</CardTitle>
              <CardDescription>Continuous RS232 stream on /dev/ttyAMA0</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 bg-muted/40 rounded-lg">
                  <span className="text-2xs text-muted-foreground uppercase">Port</span>
                  <p className="font-mono text-sm font-semibold mt-1">/dev/ttyAMA0</p>
                </div>
                <div className="p-3 bg-muted/40 rounded-lg">
                  <span className="text-2xs text-muted-foreground uppercase">Baud Rate</span>
                  <p className="font-mono text-sm font-semibold mt-1">1200 bps</p>
                </div>
                <div className="p-3 bg-muted/40 rounded-lg">
                  <span className="text-2xs text-muted-foreground uppercase">Buffer Len</span>
                  <p className="font-mono text-sm font-semibold mt-1">0 bytes (clean)</p>
                </div>
                <div className="p-3 bg-muted/40 rounded-lg">
                  <span className="text-2xs text-muted-foreground uppercase">Drain Trap</span>
                  <p className="font-mono text-sm font-semibold text-emerald-400 mt-1">ARMED (30s)</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Cameras & Crop */}
        <TabsContent value="cameras" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Vehicle Optical Crop Tuning</CardTitle>
              <CardDescription>Adjust dynamic bounding box margin for OCR recognition</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Crop Expansion Margin</span>
                  <span className="font-mono font-semibold">{cropThreshold[0]}%</span>
                </div>
                <Slider
                  value={cropThreshold}
                  onValueChange={setCropThreshold}
                  max={100}
                  min={10}
                  step={1}
                />
              </div>
              <Button size="sm" variant="outline">Persist Crop Config</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Cloud Sync */}
        <TabsContent value="cloud" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Gluvok Cloud Transmission</CardTitle>
              <CardDescription>HTTP Basic Auth & Offline Spool Durability</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Center ID</span>
                <span className="font-mono">CENTER_01</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>Offline Spool Queue</span>
                <Badge variant="secondary">0 pending records</Badge>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Wi-Fi Network */}
        <TabsContent value="wifi" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Network & Emergency AP</CardTitle>
              <CardDescription>nmcli Hotspot Failover Management</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Current Mode</span>
                <Badge variant="emerald">STA Connected</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>SSID</span>
                <span className="font-mono">Plant_Weighbridge_Industrial</span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 5: Telemetry */}
        <TabsContent value="telemetry" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">System Telemetry Log Stream</CardTitle>
              <CardDescription>In-memory ring buffer of edge transitions</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="p-3 rounded-lg bg-black/60 font-mono text-xs text-muted-foreground overflow-x-auto">
                [2026-11-19 12:40:01] [Core] Weighbridge edge daemon active.
                [2026-11-19 12:40:02] [ScaleUART] Streaming /dev/ttyAMA0 @ 1200 baud.
                [2026-11-19 12:40:05] [DrainTrap] SIGTERM trap armed with 30s period.
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 6: Config */}
        <TabsContent value="config" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Edge Device Configuration</CardTitle>
              <CardDescription>Hardware addresses, timeouts, and API endpoints</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span>Local REST Daemon</span>
                <span className="font-mono">http://127.0.0.1:8080</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>Argus Inference Microservice</span>
                <span className="font-mono">http://127.0.0.1:8000</span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
