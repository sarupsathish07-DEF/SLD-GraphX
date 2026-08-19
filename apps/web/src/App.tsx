import { Activity, CheckCircle2, CircleAlert, Network, ScanLine, ShieldCheck, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { Topology } from "./components/Topology";
import { fetchBootstrapDemo, fetchHealth } from "./lib/api";
import type { DemoResponse } from "./types/graph";
import "./styles/app.css";

function App() {
  const [demo, setDemo] = useState<DemoResponse | null>(null);
  const [health, setHealth] = useState("Connecting");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchHealth(), fetchBootstrapDemo()])
      .then(([status, result]) => { setHealth(status.mode.toUpperCase()); setDemo(result); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Local service unavailable"));
  }, []);

  const feederPath = demo?.graph.feeder_paths[0];
  const nameById = new Map(demo?.graph.equipment.map((item) => [item.id, item.equipment_id]));
  return <main className="app-shell">
    <header className="topbar"><div className="brand"><Zap size={20} /><span>SLDGRAPH</span><b>-X</b></div><div className="project-title"><small>ACTIVE PROJECT</small><strong>SUBSTATION ALPHA · BOOTSTRAP</strong></div><div className="local-status"><span className="pulse" /> {health}</div></header>
    <aside className="sidebar"><button className="nav-active"><Network /> Intelligence</button><button><ScanLine /> Import</button><button><Activity /> Trace</button><button><CircleAlert /> Review</button><button><ShieldCheck /> Validation</button><div className="sidebar-footer">v0.1.0<br />LOCAL-FIRST</div></aside>
    <section className="content">
      <div className="headline"><div><p className="eyebrow">CANONICAL ELECTRICAL GRAPH</p><h1>Source-to-feeder intelligence,<br /><em>made inspectable.</em></h1></div><div className="health-card"><CheckCircle2 /><div><small>BACKEND</small><strong>{error ? "OFFLINE" : "HEALTHY"}</strong></div></div></div>
      {error ? <div className="error-state"><CircleAlert /> {error}. Start the API with <code>.\scripts\dev.ps1</code>.</div> : demo ? <>
        <div className="metrics"><Metric value="6" label="EQUIPMENT" /><Metric value="1" label="FEEDER PATH" /><Metric value="100%" label="PATH CONFIDENCE" /><Metric value="0" label="OPEN REVIEWS" warn /></div>
        <div className="workspace-grid"><article className="panel canvas-panel"><div className="panel-heading"><div><p>RECONSTRUCTED SLD</p><small>Deterministic SLDForge fixture</small></div><span className="tag">SVG OUTPUT</span></div><div className="sld-canvas" dangerouslySetInnerHTML={{ __html: demo.svg }} /></article>
          <article className="panel trace-panel"><div className="panel-heading"><div><p>ACTIVE FEEDER TRACE</p><small>Graph reasoning result</small></div><span className="tag success">VERIFIED FIXTURE</span></div><h2>FDR-01</h2><dl><div><dt>PRIMARY SOURCE</dt><dd>{feederPath?.source_equipment_id ? nameById.get(feederPath.source_equipment_id) : "Unresolved"}</dd></div><div><dt>PATH CONFIDENCE</dt><dd>{Math.round((feederPath?.confidence ?? 0) * 100)}%</dd></div></dl><ol className="lineage">{feederPath?.equipment_path.map((id) => <li key={id}>{nameById.get(id)}</li>)}</ol><p className="muted">The line is derived from active graph connectivity. It is not a power-flow result.</p></article></div>
        <article className="panel graph-panel"><div className="panel-heading"><div><p>TOPOLOGY EXPLORER</p><small>Same canonical graph · pan, zoom, select</small></div><span className="tag">REACT FLOW</span></div><div className="flow-canvas"><Topology graph={demo.graph} /></div></article>
      </> : <div className="loading">Establishing local analysis workspace…</div>}
    </section>
  </main>;
}

function Metric({ value, label, warn = false }: { value: string; label: string; warn?: boolean }) { return <div className={`metric ${warn ? "warn" : ""}`}><strong>{value}</strong><span>{label}</span></div>; }

export default App;
