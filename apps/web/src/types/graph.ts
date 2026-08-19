export type Equipment = { id: string; equipment_id: string; type: string; confidence: number };
export type FeederPath = { feeder_equipment_id: string; source_equipment_id: string | null; equipment_path: string[]; confidence: number; active: boolean };
export type Graph = { id: string; equipment: Equipment[]; connections: { id: string; from_terminal_id: string; to_terminal_id: string; confidence: number }[]; feeder_paths: FeederPath[] };
export type DemoResponse = { graph: Graph; svg: string };
