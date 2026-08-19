import type { DemoResponse } from "../types/graph";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function fetchHealth(): Promise<{ status: string; mode: string }> {
  const response = await fetch(`${apiBase}/api/health`);
  if (!response.ok) throw new Error("Local API health check failed");
  return response.json() as Promise<{ status: string; mode: string }>;
}

export async function fetchBootstrapDemo(): Promise<DemoResponse> {
  const response = await fetch(`${apiBase}/api/bootstrap/demo`);
  if (!response.ok) throw new Error("Bootstrap demo could not be loaded");
  return response.json() as Promise<DemoResponse>;
}
