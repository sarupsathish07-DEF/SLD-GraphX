const base = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type Project = { id: string; name: string; description: string; created_at: string };
export type Drawing = { id: string; project_id: string; original_filename: string; input_type: string; file_size_bytes: number; page_count: number; width: number | null; height: number | null; native_text_count: number; has_vector_drawings: boolean; embedded_image_count: number; recommended_pipeline: string };
export type Analysis = { id: string; drawing_id: string; status: string; error_message?: string | null; stages: { stage: string; status: string; progress: number; message: string }[] };
export type Artifact = { id: string; type: string; mime_type: string; metadata: { width: number; height: number; page: number; generation_configuration: Record<string, unknown> } };
export type DrawingHistory = { drawing: Drawing; analyses: { id: string; status: string; created_at: string; finished_at: string | null }[] };
export type TextEvidence = { id: string; raw_text: string; normalized_text: string; text_type: string; confidence_ocr: number; confidence_normalization: number; confidence_semantic: number; bbox_normalized: [number, number, number, number]; polygon_normalized: [number, number][]; page: number; engine: string; model: string; review_status: string; engineer_value: string | null; engineer_text_type: string | null; association: { selected_entity: string | null } };
export type SymbolEvidence = { id: string; page: number; predicted_class: string; original_predicted_class: string | null; confidence: number | null; bbox_normalized: [number, number, number, number]; polygon_normalized: [number, number][]; orientation_deg: number; tile_origin: [number, number] | null; engine: string; model: string; provenance: string; review_status: string; review_reason: string | null; associations: { text_evidence_id: string; score: number; status: string }[] };

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
  symbolSummary: (id: string) => request<{ detected: number; by_class: Record<string, number>; associated_labels: number; needs_review: number }>(`/api/analyses/${id}/symbol-summary`),
  textSummary: (id: string) => request<{ recognized: number; by_type: Record<string, number>; needs_review: number }>(`/api/analyses/${id}/text-summary`),
  updateText: (id: string, value: string, textType: string) => request<TextEvidence>(`/api/texts/${id}`, { method: "PATCH", body: new URLSearchParams({ value, text_type: textType }) }),
  reviewText: (id: string, action: "accept" | "reject" | "unknown") => request<TextEvidence>(`/api/texts/${id}/${action}`, { method: "POST" }),
  updateSymbol: (id: string, predictedClass?: string, bbox?: number[]) => request<SymbolEvidence>(`/api/symbols/${id}`, { method: "PATCH", body: new URLSearchParams({ ...(predictedClass ? { predicted_class: predictedClass } : {}), ...(bbox ? { bbox_json: JSON.stringify(bbox) } : {}) }) }),
  reviewSymbol: (id: string, action: "accept" | "reject" | "verify") => request<SymbolEvidence>(`/api/symbols/${id}/${action}`, { method: "POST" }),
  artifactUrl: (id: string) => `${base}/api/artifacts/${id}`,
};
