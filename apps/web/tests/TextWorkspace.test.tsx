import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TextWorkspace } from "../src/TextWorkspace";

const artifact = { id: "artifact", type: "display", mime_type: "image/png", metadata: { width: 100, height: 100, page: 1, generation_configuration: {} } };
const text = { id: "text-1", raw_text: "FDR-11KV-03", normalized_text: "FDR-11KV-03", text_type: "feeder_id", confidence_ocr: .91, confidence_normalization: .98, confidence_semantic: .99, bbox_normalized: [.1, .1, .3, .2] as [number, number, number, number], polygon_normalized: [[.1, .1], [.3, .1], [.3, .2], [.1, .2]] as [number, number][], page: 1, engine: "test", model: "fixture", review_status: "pending", engineer_value: null, engineer_text_type: null, association: { selected_entity: null } };

describe("text workspace", () => {
  it("shows and selects local text evidence", () => {
    render(<TextWorkspace drawing={{ id: "d", project_id: "p", original_filename: "drawing.png", input_type: "raster_image", file_size_bytes: 1, page_count: 1, width: 100, height: 100, native_text_count: 0, has_vector_drawings: false, embedded_image_count: 1, recommended_pipeline: "raster" }} analysis={{ id: "a", drawing_id: "d", status: "complete", stages: [] }} artifacts={[artifact]} texts={[text]} onTexts={vi.fn()} />);
    expect(screen.getByText("1 recognized")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Text FDR-11KV-03"));
    expect(screen.getByText("Raw OCR")).toBeInTheDocument();
    expect(screen.getByDisplayValue("FDR-11KV-03")).toBeInTheDocument();
  });
});
