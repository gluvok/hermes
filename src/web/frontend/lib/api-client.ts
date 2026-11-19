/**
 * api-client.ts — Typed Client for Hermes Edge REST Engine
 * Connects Next.js frontend to local Flask edge endpoints.
 */

export interface SystemStatus {
  scale: {
    weight: number;
    unit: string;
    stable: boolean;
    zero: boolean;
    connected: boolean;
    last_update: number;
  };
  anpr: {
    status: string;
    last_plate: string;
    confidence: number;
  };
  cloud: {
    configured: boolean;
    center_id: string;
  };
  wifi: {
    mode: string;
    ssid: string;
    connected: boolean;
  };
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch("/api/status", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch status: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSystemConfig(): Promise<Record<string, unknown>> {
  const res = await fetch("/api/config", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch config: ${res.statusText}`);
  }
  return res.json();
}

export async function sendZeroScale(): Promise<{ success: boolean }> {
  const res = await fetch("/api/scale/zero", { method: "POST" });
  return res.json();
}

export async function sendTareScale(): Promise<{ success: boolean }> {
  const res = await fetch("/api/scale/tare", { method: "POST" });
  return res.json();
}
