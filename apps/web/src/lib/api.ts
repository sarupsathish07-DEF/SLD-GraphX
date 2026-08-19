const base = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type Project = { id: string; name: string; description: string; created_at: string };
export type Drawing = { id: string; project_id: string; original_filename: string; input_type: string; file_size_bytes: number; page_count: number; width: number | null; height: number | null; native_text_count: number; has_vector_drawings: boolean; embedded_image_count: number; recommended_pipeline: string };
export type Analysis = { id: string; drawing_id: string; status: string; error_message?: string | null; stages: { stage: string; status: string; progress: number; message: string }[] };
export type Artifact = { id: string; type: string; mime_type: string; metadata: { width: number; height: number; page: number; generation_configuration: Record<string, unknown> } };
export type DrawingHistory = { drawing: Drawing; analyses: { id: string; status: string; created_at: string; finished_at: string | null }[] };
export type TextEvidence = { id: string; raw_text: string; normalized_text: string; text_type: string; confidence_ocr: number; confidence_normalization: number; confidence_semantic: number; bbox_normalized: [number, number, number, number]; polygon_normalized: [number, number][]; page: number; engine: string; model: string; review_status: string; engineer_value: string | null; engineer_text_type: string | null; association: { selected_entity: string | null } };
export type SymbolEvidence = { id: string; page: number; predicted_class: string; original_predicted_class: string | null; confidence: number | null; bbox_normalized: [number, number, number, number]; polygon_normalized: [number, number][]; orientation_deg: number; tile_origin: [number, number] | null; engine: string; model: string; provenance: string; review_status: string; review_reason: string | null; associations: { text_evidence_id: string; score: number; status: string }[] };
export type ConductorEvidence = { id: string; page: number; polyline: [number, number][]; confidence: number; provenance: string; masked_interruption: boolean; review_status: string };
export type BusbarEvidence = { id: string; page: number; polyline: [number, number][]; bbox_normalized: [number, number, number, number]; confidence: number; provenance: string; review_status: string; associated_symbol_id: string | null };
export type JunctionEvidence = { id: string; page: number; position: [number, number]; kind: "connected_junction" | "crossover_no_connection" | "ambiguous_crossing"; degree: number; confidence: number; provenance: string; review_status: string };
export type PhysicalConnection = { id: string; analysis_run_id: string; drawing_id: string; candidate_id: string | null; page: number; from_node_id: string; to_node_id: string; polyline: [number, number][]; confidence: number; provenance: string; review_status: string; review_reason: string | null; created_at: string };
export type PhysicalGraph = { id: string; kind: "physical_connectivity"; nodes: { id: string; symbol_id: string; label: string; symbol_class: string; name: string; position: [number, number]; orientation_deg: number; provenance: string }[]; edges: PhysicalConnection[]; issues: { id: string; kind: string; message: string; related_edge_id: string | null; severity: string; status: string }[] };
export type Feeder = { id: string; equipment_id: string; feeder_id: string; source_bus_equipment_id: string | null; destination_equipment_id: string | null; voltage: string | null; rating: string | null; resolution: "resolved" | "ambiguous" | "unresolved"; confidence: number; provenance: string[]; review_status: string; path: { source_equipment_id: string | null; equipment_path: string[]; connection_path: string[]; switching_equipment_ids: string[]; weakest_connection_id: string | null; weakest_connection_confidence: number | null; uncertainty_flags: string[]; confidence: number; active: boolean } | null };
export type ElectricalReviewIssue = { id: string; issue_type: string; target_type: string; target_id: string; confidence: number; risk_score: number; priority: string; risk_factors: Record<string, number>; affected_feeders: string[]; affected_nodes: string[]; source_assignment_changes: string[]; component_change: number; status: string; review_action: string | null };
export type ElectricalGraph = { id: string; kind: "semantic_electrical"; equipment_labels: Record<string, string>; sources: { equipment_id: string; feeder_id: string | null; source_role: string; resolution: string; confidence: number; evidence: string[]; provenance: string[] }[]; feeders: Feeder[]; validation: { id: string; code: string; severity: string; message: string; target_type: string | null; target_id: string | null; status: string }[]; review_issues: ElectricalReviewIssue[]; switch_states: { equipment_id: string; state: "open" | "closed" | "unknown"; provenance: string }[]; health: { status: string; sources: number; feeders: number; resolved_paths: number; review_items: number; critical_issues: number; factors?: Record<string, number> } };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, init);
  if (!response.ok) throw new Error((await response.text()) || "Request failed");
  return response.json() as Promise<T>;
}

export const api = {
  projects: () => request<Project[]>("/api/projects"),
  createProject: (name: string, description: string) => request<Project>("/api/projects", { method: "POST", body: new URLSearchParams({ name, description }) }),
  drawings: (projectId: string) => request<Drawing[]>(`/api/projects/${projectId}/drawings`),
  drawing: (drawingId: string) => request<DrawingHistory>(`/api/drawings/${drawingId}`),
  upload: (projectId: string, file: File) => { const body = new FormData(); body.append("file", file); return request<Drawing>(`/api/projects/${projectId}/drawings`, { method: "POST", body }); },
  analyze: (drawingId: string) => request<{ analysis_run_id: string }>(`/api/drawings/${drawingId}/analyze`, { method: "POST" }),
  analysis: (id: string) => request<Analysis>(`/api/analyses/${id}`),
  artifacts: (id: string) => request<Artifact[]>(`/api/analyses/${id}/artifacts`),
  texts: (id: string) => request<TextEvidence[]>(`/api/analyses/${id}/texts`),
  symbols: (id: string) => request<SymbolEvidence[]>(`/api/analyses/${id}/symbols`),
  conductors: (id: string) => request<ConductorEvidence[]>(`/api/analyses/${id}/conductors`),
  buses: (id: string) => request<BusbarEvidence[]>(`/api/analyses/${id}/buses`),
  junctions: (id: string) => request<JunctionEvidence[]>(`/api/analyses/${id}/junctions`),
  physicalGraph: (id: string) => request<PhysicalGraph>(`/api/analyses/${id}/physical-graph`),
  electricalGraph: (id: string) => request<ElectricalGraph>(`/api/analyses/${id}/electrical-graph`),
  feederTrace: (id: string) => request<Feeder>(`/api/feeders/${id}/trace`),
  simulate: (id: string, overrides: Record<string, string>) => request<{ feeders: { equipment_id: string; feeder_id: string; resolution: string; confidence: number }[]; paths: { feeder_equipment_id: string; source_equipment_id: string | null; equipment_path: string[]; uncertainty_flags: string[] }[] }>(`/api/analyses/${id}/simulate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(overrides) }),
  setSwitchState: (analysisId: string, equipmentId: string, state: "open" | "closed" | "unknown") => request<ElectricalGraph>(`/api/analyses/${analysisId}/switches/${equipmentId}`, { method: "PATCH", body: new URLSearchParams({ state }) }),
  reviewIssue: (id: string, action: "accept" | "reject") => request<{ id: string; status: string }>(`/api/reviews/${id}/${action}`, { method: "POST" }),
  exportJson: (id: string) => `${base}/api/analyses/${id}/export/json`,
  exportBundle: (id: string) => `${base}/api/analyses/${id}/export/bundle`,
  reconstructionUrl: (id: string) => `${base}/api/analyses/${id}/reconstructed`,
  symbolSummary: (id: string) => request<{ detected: number; by_class: Record<string, number>; associated_labels: number; needs_review: number }>(`/api/analyses/${id}/symbol-summary`),
  textSummary: (id: string) => request<{ recognized: number; by_type: Record<string, number>; needs_review: number }>(`/api/analyses/${id}/text-summary`),
  updateText: (id: string, value: string, textType: string) => request<TextEvidence>(`/api/texts/${id}`, { method: "PATCH", body: new URLSearchParams({ value, text_type: textType }) }),
  reviewText: (id: string, action: "accept" | "reject" | "unknown") => request<TextEvidence>(`/api/texts/${id}/${action}`, { method: "POST" }),
  updateSymbol: (id: string, predictedClass?: string, bbox?: number[]) => request<SymbolEvidence>(`/api/symbols/${id}`, { method: "PATCH", body: new URLSearchParams({ ...(predictedClass ? { predicted_class: predictedClass } : {}), ...(bbox ? { bbox_json: JSON.stringify(bbox) } : {}) }) }),
  reviewSymbol: (id: string, action: "accept" | "reject" | "verify") => request<SymbolEvidence>(`/api/symbols/${id}/${action}`, { method: "POST" }),
  reviewConnection: (id: string, action: "accept" | "reject" | "verify") => request<PhysicalConnection>(`/api/connections/${id}`, { method: "PATCH", body: new URLSearchParams({ action }) }),
  addManualConnection: (analysisId: string, drawingId: string, fromNodeId: string, toNodeId: string) => request<PhysicalConnection>(`/api/analyses/${analysisId}/connections`, { method: "POST", body: new URLSearchParams({ drawing_id: drawingId, from_node_id: fromNodeId, to_node_id: toNodeId }) }),
  decideCrossing: (junctionId: string, decision: "connected" | "unconnected" | "unable_to_determine") => request<JunctionEvidence>(`/api/junctions/${junctionId}/crossing`, { method: "POST", body: new URLSearchParams({ decision }) }),
  artifactUrl: (id: string) => `${base}/api/artifacts/${id}`,
};
