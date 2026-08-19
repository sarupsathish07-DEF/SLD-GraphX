import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TextWorkspace } from "../src/TextWorkspace";
import { api } from "../src/lib/api";

const artifact = { id: "artifact", type: "display", mime_type: "image/png", metadata: { width: 100, height: 100, page: 1, generation_configuration: {} } };
const drawing = { id: "d", project_id: "p", original_filename: "drawing.png", input_type: "raster_image", file_size_bytes: 1, page_count: 1, width: 100, height: 100, native_text_count: 0, has_vector_drawings: false, embedded_image_count: 1, recommended_pipeline: "raster" };
const text = { id: "text-1", raw_text: "FDR-11KV-03", normalized_text: "FDR-11KV-03", text_type: "feeder_id", confidence_ocr: .91, confidence_normalization: .98, confidence_semantic: .99, bbox_normalized: [.1, .1, .3, .2] as [number, number, number, number], polygon_normalized: [[.1, .1], [.3, .1], [.3, .2], [.1, .2]] as [number, number][], page: 1, engine: "test", model: "fixture", review_status: "pending", engineer_value: null, engineer_text_type: null, association: { selected_entity: null } };
const symbol = { id: "symbol-1", analysis_run_id: "a", drawing_id: "d", page: 1, predicted_class: "circuit_breaker", original_predicted_class: "circuit_breaker", confidence: .87, bbox_normalized: [.45, .3, .55, .5] as [number, number, number, number], polygon_normalized: [], orientation_deg: 0, tile_origin: null, engine: "test", model: "fixture", provenance: "local_symbol_detector", review_status: "pending", review_reason: null, associations: [], created_at: "2026-08-19T00:00:00Z" };
const physicalGraph = { id: "physical:a", kind: "physical_connectivity" as const, nodes: [{ id: "terminal:source:attach", symbol_id: "source", label: "energy_source", symbol_class: "energy_source", name: "ATTACH", position: [.1, .5] as [number, number], orientation_deg: 0, provenance: "fixture" }, { id: "terminal:feeder:attach", symbol_id: "feeder", label: "feeder_terminal", symbol_class: "feeder_terminal", name: "ATTACH", position: [.9, .5] as [number, number], orientation_deg: 0, provenance: "fixture" }], edges: [{ id: "edge-1", analysis_run_id: "a", drawing_id: "d", candidate_id: "candidate-1", page: 1, from_node_id: "terminal:source:attach", to_node_id: "terminal:feeder:attach", polyline: [[.1, .5], [.9, .5]] as [number, number][], confidence: .82, provenance: "line_trace+terminal_snap", review_status: "pending", review_reason: null, created_at: "2026-08-19T00:00:00Z" }], issues: [] };
const electrical = { id: "electrical:a", kind: "semantic_electrical" as const, equipment_labels: { source: "GRID-01", bus: "BUS-A", feeder: "FDR-11KV-03" }, sources: [{ equipment_id: "source", feeder_id: null, source_role: "energy_source", resolution: "candidate", confidence: .9, evidence: [], provenance: ["graph_reasoning"] }], feeders: [{ id: "feeder:a", equipment_id: "feeder", feeder_id: "FDR-11KV-03", source_bus_equipment_id: "bus", destination_equipment_id: null, voltage: "11 kV", rating: "630 A", resolution: "resolved" as const, confidence: .82, provenance: ["graph_reasoning"], review_status: "inferred", path: { source_equipment_id: "source", equipment_path: ["source", "bus", "feeder"], connection_path: ["edge-1"], switching_equipment_ids: [], weakest_connection_id: "edge-1", weakest_connection_confidence: .82, uncertainty_flags: [], confidence: .82, active: true } }], validation: [], review_issues: [], switch_states: [], health: { status: "Healthy", sources: 1, feeders: 1, resolved_paths: 1, review_items: 0, critical_issues: 0 } };

function workspace(options: { texts?: typeof text[]; symbols?: typeof symbol[]; graph?: typeof physicalGraph | null } = {}) { return render(<TextWorkspace drawing={drawing} analysis={{ id: "a", drawing_id: "d", status: "complete", stages: [] }} artifacts={[artifact]} texts={options.texts ?? []} symbols={options.symbols ?? []} conductors={[]} buses={[]} junctions={[]} physicalGraph={options.graph ?? null} onTexts={vi.fn()} onSymbols={vi.fn()} onGraph={vi.fn()} onJunctions={vi.fn()} />); }

describe("electrical intelligence workspace", () => {
  beforeEach(() => {
    vi.spyOn(api, "electricalGraph").mockResolvedValue(electrical);
    vi.spyOn(api, "feederTrace").mockResolvedValue(electrical.feeders[0]);
  });
  it("shows and selects local text evidence", async () => {
    workspace({ texts: [text] });
    expect(await screen.findByText("Electrical intelligence workspace")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Text FDR-11KV-03"));
    expect(screen.getByText("Raw OCR")).toBeInTheDocument();
  });
  it("shows and selects symbol evidence separately from text", () => {
    workspace({ texts: [text], symbols: [symbol] });
    fireEvent.click(screen.getByLabelText("Symbol Circuit Breaker"));
    expect(screen.getByText("Component candidate")).toBeInTheDocument();
  });
  it("switches to the synchronized graph and renders its physical edge", () => {
    const { container } = workspace({ graph: physicalGraph });
    fireEvent.click(container.querySelector(".workspace-tabs button:last-child")!);
    expect(screen.getByText("Operational / physical graph")).toBeInTheDocument();
    expect(container.querySelectorAll(".graph-edge")).toHaveLength(1);
  });
  it("opens an explainable feeder trace from the local search", async () => {
    const { container } = workspace();
    const input = await screen.findByLabelText("Search feeder / equipment");
    fireEvent.change(input, { target: { value: "FDR" } });
    fireEvent.click(container.querySelector(".trace-list button")!);
    expect(await screen.findByText("Path confidence")).toBeInTheDocument();
    expect(screen.getByText("GRID-01 → BUS-A → FDR-11KV-03")).toBeInTheDocument();
  });
});
