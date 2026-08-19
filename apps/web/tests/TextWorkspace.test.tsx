import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TextWorkspace } from "../src/TextWorkspace";

const artifact = { id: "artifact", type: "display", mime_type: "image/png", metadata: { width: 100, height: 100, page: 1, generation_configuration: {} } };
const text = { id: "text-1", raw_text: "FDR-11KV-03", normalized_text: "FDR-11KV-03", text_type: "feeder_id", confidence_ocr: .91, confidence_normalization: .98, confidence_semantic: .99, bbox_normalized: [.1, .1, .3, .2] as [number, number, number, number], polygon_normalized: [[.1, .1], [.3, .1], [.3, .2], [.1, .2]] as [number, number][], page: 1, engine: "test", model: "fixture", review_status: "pending", engineer_value: null, engineer_text_type: null, association: { selected_entity: null } };
const symbol = { id: "symbol-1", analysis_run_id: "a", drawing_id: "d", page: 1, predicted_class: "circuit_breaker", original_predicted_class: "circuit_breaker", confidence: .87, bbox_normalized: [.45, .3, .55, .5] as [number, number, number, number], polygon_normalized: [], orientation_deg: 0, tile_origin: null, engine: "test", model: "fixture", provenance: "local_symbol_detector", review_status: "pending", review_reason: null, associations: [], created_at: "2026-08-19T00:00:00Z" };
const physicalGraph = { id: "physical:a", kind: "physical_connectivity" as const, nodes: [{ id: "terminal:source:attach", symbol_id: "source", label: "energy_source", symbol_class: "energy_source", name: "ATTACH", position: [.1, .5] as [number, number], orientation_deg: 0, provenance: "fixture" }, { id: "terminal:feeder:attach", symbol_id: "feeder", label: "feeder_terminal", symbol_class: "feeder_terminal", name: "ATTACH", position: [.9, .5] as [number, number], orientation_deg: 0, provenance: "fixture" }], edges: [{ id: "edge-1", analysis_run_id: "a", drawing_id: "d", candidate_id: "candidate-1", page: 1, from_node_id: "terminal:source:attach", to_node_id: "terminal:feeder:attach", polyline: [[.1, .5], [.9, .5]] as [number, number][], confidence: .82, provenance: "line_trace+terminal_snap", review_status: "pending", review_reason: null, created_at: "2026-08-19T00:00:00Z" }], issues: [] };

describe("text workspace", () => {
  it("shows and selects local text evidence", () => {
    render(<TextWorkspace drawing={{ id: "d", project_id: "p", original_filename: "drawing.png", input_type: "raster_image", file_size_bytes: 1, page_count: 1, width: 100, height: 100, native_text_count: 0, has_vector_drawings: false, embedded_image_count: 1, recommended_pipeline: "raster" }} analysis={{ id: "a", drawing_id: "d", status: "complete", stages: [] }} artifacts={[artifact]} texts={[text]} symbols={[]} conductors={[]} buses={[]} junctions={[]} physicalGraph={null} onTexts={vi.fn()} onSymbols={vi.fn()} onGraph={vi.fn()} onJunctions={vi.fn()} />);
    expect(screen.getByText("Physical topology workspace")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Text FDR-11KV-03"));
    expect(screen.getByText("Raw OCR")).toBeInTheDocument();
    expect(screen.getByDisplayValue("FDR-11KV-03")).toBeInTheDocument();
  });

  it("shows and selects symbol evidence separately from text", () => {
    render(<TextWorkspace drawing={{ id: "d", project_id: "p", original_filename: "drawing.png", input_type: "raster_image", file_size_bytes: 1, page_count: 1, width: 100, height: 100, native_text_count: 0, has_vector_drawings: false, embedded_image_count: 1, recommended_pipeline: "raster" }} analysis={{ id: "a", drawing_id: "d", status: "complete", stages: [] }} artifacts={[artifact]} texts={[text]} symbols={[symbol]} conductors={[]} buses={[]} junctions={[]} physicalGraph={null} onTexts={vi.fn()} onSymbols={vi.fn()} onGraph={vi.fn()} onJunctions={vi.fn()} />);
    fireEvent.click(screen.getByLabelText("Symbol Circuit Breaker"));
    expect(screen.getByText("Component candidate")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Circuit Breaker" })).toBeInTheDocument();
  });

  it("renders the physical evidence graph alongside the SLD", () => {
    const { container } = render(<TextWorkspace drawing={{ id: "d", project_id: "p", original_filename: "drawing.png", input_type: "raster_image", file_size_bytes: 1, page_count: 1, width: 100, height: 100, native_text_count: 0, has_vector_drawings: false, embedded_image_count: 1, recommended_pipeline: "raster" }} analysis={{ id: "a", drawing_id: "d", status: "complete", stages: [] }} artifacts={[artifact]} texts={[]} symbols={[]} conductors={[]} buses={[]} junctions={[]} physicalGraph={physicalGraph} onTexts={vi.fn()} onSymbols={vi.fn()} onGraph={vi.fn()} onJunctions={vi.fn()} />);
    expect(screen.getByText("Physical graph")).toBeInTheDocument();
    expect(container.querySelectorAll(".graph-edge")).toHaveLength(1);
    expect(container.textContent).toContain("Physical connections are image-derived candidates.");
  });
});
