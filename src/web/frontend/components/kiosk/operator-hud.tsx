"use client";

import * as React from "react";
import { Scale, Camera, Truck, Printer, Edit, RefreshCw } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface OperatorHUDProps {
  weight?: number;
  unit?: string;
  isStable?: boolean;
  plateNumber?: string;
  anprConfidence?: number;
  onZero?: () => void;
  onTare?: () => void;
  onPrint?: () => void;
  onOverridePlate?: () => void;
}

export function OperatorHUD({
  weight = 0.0,
  unit = "kg",
  isStable = true,
  plateNumber = "KA-01-MJ-5021",
  anprConfidence = 0.94,
  onZero,
  onTare,
  onPrint,
  onOverridePlate,
}: OperatorHUDProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full max-w-7xl mx-auto p-4">
      {/* 60% Left Hero: Live Scale Display */}
      <div className="lg:col-span-7 flex flex-col gap-6">
        <Card className="border-border bg-card/60 backdrop-blur-md">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="space-y-1">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Scale className="h-4 w-4 text-primary" />
                Live Weighbridge Indicator
              </CardTitle>
              <CardDescription>/dev/ttyAMA0 @ 1200 baud</CardDescription>
            </div>
            {isStable ? (
              <Badge variant="emerald" className="font-mono">STABLE</Badge>
            ) : (
              <Badge variant="amber" className="animate-pulse font-mono">SAMPLING</Badge>
            )}
          </CardHeader>

          <CardContent className="flex flex-col items-center justify-center py-10">
            <div className="text-6xl sm:text-7xl font-mono font-bold tracking-tight text-foreground">
              {weight.toFixed(2)}
              <span className="text-2xl font-sans font-normal text-muted-foreground ml-3">
                {unit}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              Hardware filter: 10s stability debounce window
            </p>
          </CardContent>

          {/* Touch-Friendly Scale Action Triggers */}
          <div className="p-4 border-t border-border/50 flex gap-3">
            <Button
              variant="outline"
              size="lg"
              onClick={onZero}
              className="flex-1 min-h-12 text-sm font-medium"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Zero Scale
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={onTare}
              className="flex-1 min-h-12 text-sm font-medium"
            >
              Tare Scale
            </Button>
          </div>
        </Card>

        {/* Latest Weighment Session Card */}
        <Card className="border-border bg-card/40">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs uppercase font-medium text-muted-foreground flex items-center gap-2">
              <Truck className="h-4 w-4" />
              Verified Weighment Record
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-xs text-muted-foreground">Vehicle Plate</span>
              <div className="text-xl font-mono font-semibold text-primary mt-1">
                {plateNumber || "READY"}
              </div>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">ANPR Confidence</span>
              <div className="text-sm font-medium mt-1">
                {(anprConfidence * 100).toFixed(1)}% match
              </div>
            </div>
          </CardContent>
          <div className="p-4 border-t border-border/50 flex gap-3">
            <Button
              variant="default"
              size="lg"
              onClick={onPrint}
              className="flex-1 min-h-12"
            >
              <Printer className="mr-2 h-4 w-4" />
              Print Slip
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={onOverridePlate}
              className="flex-1 min-h-12"
            >
              <Edit className="mr-2 h-4 w-4" />
              Manual Correction
            </Button>
          </div>
        </Card>
      </div>

      {/* 40% Right: Vehicle Framing & Camera Feed */}
      <div className="lg:col-span-5 flex flex-col gap-6">
        <Card className="border-border bg-card/60 flex-1 flex flex-col overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Camera className="h-4 w-4 text-primary" />
              Vehicle Framing Stream
            </CardTitle>
            <CardDescription>Camera 1 ANPR Optical Crop</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col items-center justify-center p-4">
            <div className="relative w-full aspect-video rounded-lg bg-black/40 border border-border flex items-center justify-center overflow-hidden">
              <div className="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/80 to-transparent flex justify-between items-center">
                <span className="text-xs font-mono text-white/80">RTSP: Port 8554</span>
                <Badge variant="emerald" className="text-2xs">LIVE 1080p</Badge>
              </div>
              <Camera className="h-10 w-10 text-muted-foreground/40" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
