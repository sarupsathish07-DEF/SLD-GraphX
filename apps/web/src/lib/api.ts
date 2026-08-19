const base = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type Project = { id: string; name: string; description: string; created_at: string };
export type Drawing = { id: string; project_id: string; original_filename: string; input_type: string; file_size_bytes: number; page_count: number; width: number | null; height: number | null; native_text_count: number; has_vector_drawings: boolean; embedded_image_count: number; recommended_pipeline: string };
export type Analysis = { id: string; drawing_id: string; status: string; error_message?: string | null; stages: { stage: string; status: string; progress: number; message: string }[] };
export type Artifact = { id: string; type: string; mime_type: string; metadata: { width: number; height: number; page: number; generation_configuration: Record<string, unknown> } };
export type DrawingHistory = { drawing: Drawing; analyses: { id: string; status: string; created_at: string; finished_at: string | null }[] };

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
  artifactUrl: (id: string) => `${base}/api/artifacts/${id}`,
};
