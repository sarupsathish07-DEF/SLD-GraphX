import { Background, Controls, Handle, MiniMap, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Graph } from "../types/graph";

const positions: Record<string, { x: number; y: number }> = {
  source_grid: { x: 30, y: 170 }, transformer_01: { x: 210, y: 160 }, bus_a: { x: 395, y: 170 }, breaker_01: { x: 570, y: 160 }, ct_01: { x: 750, y: 160 }, feeder_01: { x: 925, y: 160 }
};

function EquipmentNode({ data, selected }: NodeProps<Node<{ label: string; kind: string }>>) {
  return <div className={`equipment-node ${selected ? "selected" : ""}`}><Handle type="target" position={Position.Left} /><span>{data.kind.replaceAll("_", " ")}</span><strong>{data.label}</strong><Handle type="source" position={Position.Right} /></div>;
}

export function Topology({ graph }: { graph: Graph }) {
  const nodes: Node[] = graph.equipment.map((equipment) => ({ id: equipment.id, position: positions[equipment.id] ?? { x: 0, y: 0 }, type: "equipment", data: { label: equipment.equipment_id, kind: equipment.type } }));
  const terminalToEquipment = new Map<string, string>();
  graph.equipment.forEach((equipment) => { terminalToEquipment.set(`${equipment.id}_in`, equipment.id); terminalToEquipment.set(`${equipment.id}_out`, equipment.id); });
  const edges: Edge[] = graph.connections.map((connection) => ({ id: connection.id, source: terminalToEquipment.get(connection.from_terminal_id) ?? "", target: terminalToEquipment.get(connection.to_terminal_id) ?? "", animated: true, style: { stroke: "#45d8ca", strokeWidth: 2.5 } }));
  return <ReactFlow nodes={nodes} edges={edges} nodeTypes={{ equipment: EquipmentNode }} fitView minZoom={0.4} maxZoom={2.2} proOptions={{ hideAttribution: true }}><Background color="#2a4054" gap={20} /><MiniMap pannable zoomable /><Controls showInteractive={false} /></ReactFlow>;
}
