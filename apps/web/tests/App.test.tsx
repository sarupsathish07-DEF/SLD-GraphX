import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";

describe("bootstrap workspace", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => url.includes("health") ? { status: "ok", mode: "local" } : { svg: "<svg></svg>", graph: { id: "fixture", equipment: [], connections: [], feeder_paths: [{ feeder_equipment_id: "feeder_01", source_equipment_id: "source_grid", equipment_path: [], confidence: 1, active: true }] } } })));
  });
  it("shows the local graph workspace", async () => {
    render(<App />);
    expect(await screen.findByText("Source-to-feeder intelligence,")).toBeInTheDocument();
    expect(await screen.findByText("TOPOLOGY EXPLORER")).toBeInTheDocument();
  });
});
