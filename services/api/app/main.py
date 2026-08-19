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
from services.api.app.services.texts import (
    text_by_id,
    text_summary,
    texts_for_analysis,
    update_text,
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
    return {"status": "ok", "service": "sldgraph-x-api", "mode": "local", "ocr": ocr_health()}


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


@app.get("/api/texts/{text_id}")
def text(text_id: str) -> dict:
    try:
        return text_by_id(text_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


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
