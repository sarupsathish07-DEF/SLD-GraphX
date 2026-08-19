import json
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import select

from services.api.app.db import initialize_database
from services.api.app.db.database import SessionLocal
from services.api.app.db.entities import AnalysisRunRecord
from services.api.app.services.analysis import (
    analysis_payload,
    artifact_path,
    artifacts_payload,
    queue_analysis,
    run_analysis,
)
from services.api.app.services.demo import bootstrap_demo
from services.api.app.services.electrical import (
    electrical_graph,
    export_bundle,
    export_json,
    feeder_trace,
    feeders_for_analysis,
    reconstructed_svg,
    review_issue,
    set_switch_state,
    simulate,
    sources_for_analysis,
)
from services.api.app.services.ingestion import (
    create_project,
    drawings_for_project,
    get_drawing,
    get_project,
    list_projects,
    serialize_drawing,
    store_drawing,
)
from services.api.app.services.ocr_worker import health as ocr_health
from services.api.app.services.symbol_worker import health as symbol_health
from services.api.app.services.symbols import (
    add_manual_symbol,
    symbol_by_id,
    symbol_summary,
    symbols_for_analysis,
    update_symbol,
)
from services.api.app.services.texts import (
    text_by_id,
    text_summary,
    texts_for_analysis,
    update_text,
)
from services.api.app.services.topology import (
    add_manual_connection,
    buses_for_analysis,
    conductors_for_analysis,
    connection_by_id,
    decide_crossing,
    junctions_for_analysis,
    physical_graph,
    review_connection,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="SLDGraph-X API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "sldgraph-x-api",
        "mode": "local",
        "ocr": ocr_health(),
        "detector": symbol_health(),
    }


@app.get("/api/bootstrap/demo")
def demo() -> dict:
    return bootstrap_demo()


def project_payload(project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at.isoformat(),
    }


@app.post("/api/projects", status_code=201)
def create_project_route(name: str = Form(...), description: str = Form("")) -> dict:
    return project_payload(create_project(name, description))


@app.get("/api/projects")
def projects() -> list[dict]:
    return [project_payload(project) for project in list_projects()]


@app.get("/api/projects/{project_id}")
def project(project_id: str) -> dict:
    return project_payload(get_project(project_id))


@app.get("/api/projects/{project_id}/drawings")
def project_drawings(project_id: str) -> list[dict]:
    get_project(project_id)
    return [serialize_drawing(drawing) for drawing in drawings_for_project(project_id)]


@app.get("/api/drawings/{drawing_id}")
def drawing(drawing_id: str) -> dict:
    record = get_drawing(drawing_id)
    with SessionLocal() as session:
        runs = list(
            session.scalars(
                select(AnalysisRunRecord)
                .where(AnalysisRunRecord.drawing_id == drawing_id)
                .order_by(AnalysisRunRecord.created_at.desc())
            )
        )
    return {
        "drawing": serialize_drawing(record),
        "analyses": [
            {
                "id": run.id,
                "status": run.status,
                "created_at": run.created_at.isoformat(),
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            }
            for run in runs
        ],
    }


@app.post("/api/projects/{project_id}/drawings", status_code=201)
async def upload_drawing(project_id: str, file: UploadFile = File(...)) -> dict:
    return serialize_drawing(await store_drawing(project_id, file))


@app.post("/api/drawings/{drawing_id}/analyze", status_code=202)
def analyze_drawing(drawing_id: str, background_tasks: BackgroundTasks) -> dict:
    try:
        run_id = queue_analysis(drawing_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    background_tasks.add_task(run_analysis, drawing_id, run_id)
    return {"analysis_run_id": run_id, "status": "queued"}


@app.get("/api/analyses/{analysis_id}")
def analysis(analysis_id: str) -> dict:
    try:
        return analysis_payload(analysis_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/analyses/{analysis_id}/artifacts")
def artifacts(analysis_id: str) -> list[dict]:
    try:
        return artifacts_payload(analysis_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/analyses/{analysis_id}/texts")
def texts(analysis_id: str) -> list[dict]:
    return texts_for_analysis(analysis_id)


@app.get("/api/analyses/{analysis_id}/text-summary")
def analysis_text_summary(analysis_id: str) -> dict:
    return text_summary(analysis_id)


@app.get("/api/analyses/{analysis_id}/symbols")
def symbols(analysis_id: str) -> list[dict]:
    return symbols_for_analysis(analysis_id)


@app.get("/api/analyses/{analysis_id}/symbol-summary")
def analysis_symbol_summary(analysis_id: str) -> dict:
    return symbol_summary(analysis_id)


@app.get("/api/analyses/{analysis_id}/conductors")
def conductors(analysis_id: str) -> list[dict]:
    return conductors_for_analysis(analysis_id)


@app.get("/api/analyses/{analysis_id}/junctions")
def junctions(analysis_id: str) -> list[dict]:
    return junctions_for_analysis(analysis_id)


@app.get("/api/analyses/{analysis_id}/buses")
def buses(analysis_id: str) -> list[dict]:
    return buses_for_analysis(analysis_id)


@app.get("/api/analyses/{analysis_id}/physical-graph")
def analysis_physical_graph(analysis_id: str) -> dict:
    return physical_graph(analysis_id)


@app.get("/api/analyses/{analysis_id}/sources")
def analysis_sources(analysis_id: str) -> list[dict]:
    return sources_for_analysis(analysis_id)


@app.get("/api/analyses/{analysis_id}/feeders")
def analysis_feeders(analysis_id: str) -> list[dict]:
    return feeders_for_analysis(analysis_id)


@app.get("/api/analyses/{analysis_id}/electrical-graph")
def analysis_electrical_graph(analysis_id: str) -> dict:
    return electrical_graph(analysis_id)


@app.get("/api/feeders/{feeder_id}/trace")
def trace_feeder(feeder_id: str) -> dict:
    try:
        return feeder_trace(feeder_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/analyses/{analysis_id}/validation")
def analysis_validation(analysis_id: str) -> list[dict]:
    return electrical_graph(analysis_id)["validation"]


@app.get("/api/analyses/{analysis_id}/review-issues")
def analysis_review_issues(analysis_id: str) -> list[dict]:
    return electrical_graph(analysis_id)["review_issues"]


@app.post("/api/analyses/{analysis_id}/simulate")
def simulate_analysis(analysis_id: str, overrides: dict[str, str], save: bool = False, name: str | None = None) -> dict:
    try:
        return simulate(analysis_id, overrides, save, name)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.patch("/api/analyses/{analysis_id}/switches/{equipment_id}")
def update_switch(analysis_id: str, equipment_id: str, state: str = Form(...)) -> dict:
    try:
        return set_switch_state(analysis_id, equipment_id, state)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/reviews/{issue_id}/{action}")
def action_review(issue_id: str, action: str) -> dict:
    try:
        return review_issue(issue_id, action)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/analyses/{analysis_id}/export/json")
def analysis_export_json(analysis_id: str) -> dict:
    try:
        return export_json(analysis_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/analyses/{analysis_id}/reconstructed")
def analysis_reconstructed(analysis_id: str):
    try:
        svg = reconstructed_svg(analysis_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    from fastapi.responses import Response

    return Response(svg, media_type="image/svg+xml")


@app.get("/api/analyses/{analysis_id}/export/bundle")
def analysis_export_bundle(analysis_id: str):
    try:
        content, filename = export_bundle(analysis_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    from fastapi.responses import Response

    return Response(content, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/analyses/{analysis_id}/export/csv")
def analysis_export_csv(analysis_id: str):
    """CSV tables are delivered as the same safe ZIP bundle as the full export."""
    return analysis_export_bundle(analysis_id)


@app.get("/api/texts/{text_id}")
def text(text_id: str) -> dict:
    try:
        return text_by_id(text_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/symbols/{symbol_id}")
def symbol(symbol_id: str) -> dict:
    try:
        return symbol_by_id(symbol_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/connections/{connection_id}")
def connection(connection_id: str) -> dict:
    try:
        return connection_by_id(connection_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.patch("/api/connections/{connection_id}")
def patch_connection(connection_id: str, action: str = Form(...)) -> dict:
    try:
        return review_connection(connection_id, action)
    except ValueError as exc:
        status_code = 404 if str(exc) == "Physical connection not found" else 422
        raise HTTPException(status_code, str(exc)) from exc


@app.delete("/api/connections/{connection_id}")
def reject_connection(connection_id: str) -> dict:
    try:
        return review_connection(connection_id, "reject")
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/analyses/{analysis_id}/connections", status_code=201)
def manual_connection(
    analysis_id: str,
    drawing_id: str = Form(...),
    from_node_id: str = Form(...),
    to_node_id: str = Form(...),
    page: int = Form(1),
) -> dict:
    try:
        return add_manual_connection(analysis_id, drawing_id, from_node_id, to_node_id, page)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/junctions/{junction_id}/crossing")
def crossing_decision(junction_id: str, decision: str = Form(...)) -> dict:
    try:
        return decide_crossing(junction_id, decision)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.patch("/api/symbols/{symbol_id}")
def edit_symbol(
    symbol_id: str,
    predicted_class: str | None = Form(None),
    bbox_json: str | None = Form(None),
) -> dict:
    try:
        return update_symbol(
            symbol_id,
            "edit",
            predicted_class,
            json.loads(bbox_json) if bbox_json else None,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/symbols/{symbol_id}/{action}")
def review_symbol(symbol_id: str, action: str) -> dict:
    if action not in {"accept", "reject", "verify"}:
        raise HTTPException(422, "Unsupported symbol review action")
    try:
        return update_symbol(symbol_id, action)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/analyses/{analysis_id}/symbols", status_code=201)
def add_symbol(
    analysis_id: str,
    drawing_id: str = Form(...),
    page: int = Form(1),
    predicted_class: str = Form(...),
    bbox_json: str = Form(...),
) -> dict:
    try:
        return add_manual_symbol(
            analysis_id, drawing_id, page, predicted_class, json.loads(bbox_json)
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.patch("/api/texts/{text_id}")
def edit_text(
    text_id: str, value: str | None = Form(None), text_type: str | None = Form(None)
) -> dict:
    try:
        return update_text(text_id, value, text_type, "edit")
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/texts/{text_id}/{action}")
def review_text(text_id: str, action: str) -> dict:
    if action not in {"accept", "reject", "unknown"}:
        raise HTTPException(422, "Unsupported review action")
    try:
        return update_text(text_id, None, None, action)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/artifacts/{artifact_id}")
def artifact(artifact_id: str) -> FileResponse:
    try:
        path, mime_type = artifact_path(artifact_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return FileResponse(
        path, media_type=mime_type, headers={"Cache-Control": "private, max-age=3600"}
    )
