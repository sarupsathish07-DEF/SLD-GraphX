from io import BytesIO
from pathlib import Path

import fitz
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from services.api.app.db.database import SessionLocal
from services.api.app.db.entities import JunctionEvidenceRecord, TerminalEvidenceRecord
from services.api.app.main import app
from services.api.app.services.analysis import queue_analysis, run_analysis
from sldforge.generator import build_radial_fixture
from sldforge.renderer import render_png


def test_health_reports_local_service() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["mode"] == "local"


def test_bootstrap_demo_has_exact_feeder_path() -> None:
    with TestClient(app) as client:
        response = client.get("/api/bootstrap/demo")
    assert response.status_code == 200
    graph = response.json()["graph"]
    path = graph["feeder_paths"][0]
    assert path["feeder_equipment_id"] == "feeder_01"
    assert path["source_equipment_id"] == "source_grid"
    assert path["equipment_path"] == ["source_grid", "transformer_01", "bus_a", "breaker_01", "ct_01", "feeder_01"]
    assert path["connection_path"] == ["edge_01", "edge_02", "edge_03", "edge_04", "edge_05"]
    assert path["weakest_connection_confidence"] == 1.0
    assert path["active"] is True
    assert "<svg" in response.json()["svg"]


def test_project_and_png_upload_persist_safe_metadata() -> None:
    image = Image.new("RGB", (80, 40), "white")
    payload = BytesIO()
    image.save(payload, format="PNG")
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "Ingestion Test"}).json()
        upload = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("../../substation.png", payload.getvalue(), "image/png")},
        )
        listing = client.get(f"/api/projects/{project['id']}/drawings")
    assert upload.status_code == 201
    drawing = upload.json()
    assert drawing["original_filename"] == "substation.png"
    assert drawing["input_type"] == "raster_image"
    assert drawing["width"] == 80
    assert len(drawing["sha256"]) == 64
    assert listing.json()[0]["id"] == drawing["id"]


def test_jpeg_pdf_and_invalid_upload_behavior() -> None:
    image = Image.new("RGB", (96, 48), "white")
    jpeg = BytesIO()
    image.save(jpeg, format="JPEG")
    pdf = fitz.open()
    page = pdf.new_page(width=240, height=120)
    page.insert_text((30, 40), "BUS-A")
    pdf_data = pdf.tobytes()
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "Format Test"}).json()
        jpg = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("drawing.jpg", jpeg.getvalue(), "image/jpeg")},
        )
        uploaded_pdf = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("drawing.pdf", pdf_data, "application/pdf")},
        )
        invalid = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("drawing.txt", b"not supported", "text/plain")},
        )
        malformed = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("broken.pdf", b"not a PDF", "application/pdf")},
        )
    assert jpg.status_code == 201 and jpg.json()["input_type"] == "raster_image"
    assert uploaded_pdf.status_code == 201
    assert uploaded_pdf.json()["page_count"] == 1
    assert invalid.status_code == 415
    assert malformed.status_code == 422


def test_uploaded_png_can_complete_persisted_preprocessing() -> None:
    image = Image.new("RGB", (160, 80), "white")
    payload = BytesIO()
    image.save(payload, format="PNG")
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "Analysis Test"}).json()
        drawing = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("sld.png", payload.getvalue(), "image/png")},
        ).json()
        accepted = client.post(f"/api/drawings/{drawing['id']}/analyze")
        analysis_id = accepted.json()["analysis_run_id"]
        result = client.get(f"/api/analyses/{analysis_id}")
        topology = client.get(f"/api/analyses/{analysis_id}/physical-graph").json()
        conductors = client.get(f"/api/analyses/{analysis_id}/conductors").json()
        junctions = client.get(f"/api/analyses/{analysis_id}/junctions").json()
    assert accepted.status_code == 202
    assert result.json()["status"] == "complete"
    assert [stage["stage"] for stage in result.json()["stages"]] == [
        "ingestion",
        "inspection",
        "rendering",
        "preprocessing",
        "ocr",
        "text_normalization",
        "text_semantics",
        "symbol_detection",
        "text_symbol_association",
        "conductor_extraction",
        "junction_detection",
        "terminal_mapping",
        "graph_assembly",
            "graph_validation",
            "electrical_reasoning",
            "electrical_validation",
            "topology_criticality",
            "complete",
    ]
    assert topology["kind"] == "physical_connectivity"
    assert len(topology["nodes"]) == 1
    assert isinstance(conductors, list) and isinstance(junctions, list)


def test_artifacts_are_listed_and_safely_served() -> None:
    image = Image.new("RGB", (64, 64), "white")
    payload = BytesIO()
    image.save(payload, format="PNG")
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "Artifact Test"}).json()
        drawing = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("drawing.png", payload.getvalue(), "image/png")},
        ).json()
        analysis_id = client.post(f"/api/drawings/{drawing['id']}/analyze").json()[
            "analysis_run_id"
        ]
        artifacts = client.get(f"/api/analyses/{analysis_id}/artifacts").json()
        response = client.get(f"/api/artifacts/{artifacts[0]['id']}")
    assert {item["type"] for item in artifacts} >= {
        "source_reference",
        "display",
        "analysis",
        "grayscale",
        "contrast",
        "binary",
        "line_emphasized",
    }
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_completed_analysis_reopens_after_new_application_lifespan() -> None:
    image = Image.new("RGB", (72, 36), "white")
    payload = BytesIO()
    image.save(payload, format="PNG")
    with TestClient(app) as first:
        project = first.post("/api/projects", data={"name": "Restart Test"}).json()
        drawing = first.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("restart.png", payload.getvalue(), "image/png")},
        ).json()
        analysis_id = first.post(f"/api/drawings/{drawing['id']}/analyze").json()["analysis_run_id"]
    with TestClient(app) as second:
        history = second.get(f"/api/drawings/{drawing['id']}")
        artifacts = second.get(f"/api/analyses/{analysis_id}/artifacts")
        image_response = second.get(f"/api/artifacts/{artifacts.json()[0]['id']}")
    assert history.status_code == 200 and history.json()["analyses"][0]["status"] == "complete"
    assert image_response.status_code == 200


def test_real_sldforge_raster_runs_through_upload_and_analysis() -> None:
    buffer = BytesIO()
    render_png(build_radial_fixture()).save(buffer, "PNG")
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "SLDForge Loop"}).json()
        drawing = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("sldforge-radial.png", buffer.getvalue(), "image/png")},
        ).json()
        analysis_id = queue_analysis(drawing["id"])
        run_analysis(drawing["id"], analysis_id)
        result = client.get(f"/api/analyses/{analysis_id}").json()
        graph = client.get(f"/api/analyses/{analysis_id}/physical-graph").json()
        assert graph["nodes"]
        second_terminal = f"terminal:{analysis_id}:review"
        junction_id = f"junction:{analysis_id}:review"
        with SessionLocal() as session:
            session.add(
                TerminalEvidenceRecord(
                    id=second_terminal,
                    analysis_run_id=analysis_id,
                    drawing_id=drawing["id"],
                    symbol_evidence_id=graph["nodes"][0]["symbol_id"],
                    page=1,
                    symbol_class="feeder_terminal",
                    name="REVIEW",
                    position_json="[0.8, 0.5]",
                    orientation_deg=0,
                    orientation_confidence=1.0,
                    provenance="test_fixture",
                )
            )
            session.add(
                JunctionEvidenceRecord(
                    id=junction_id,
                    analysis_run_id=analysis_id,
                    drawing_id=drawing["id"],
                    page=1,
                    position_json="[0.5, 0.5]",
                    kind="ambiguous_crossing",
                    degree=4,
                    confidence=0.42,
                    provenance="test_fixture",
                    review_status="pending",
                )
            )
            session.commit()
        added = client.post(
            f"/api/analyses/{analysis_id}/connections",
            data={
                "drawing_id": drawing["id"],
                "from_node_id": graph["nodes"][0]["id"],
                "to_node_id": second_terminal,
            },
        )
        rejected = client.delete(f"/api/connections/{added.json()['id']}")
        invalid = client.post(
            f"/api/analyses/{analysis_id}/connections",
            data={
                "drawing_id": drawing["id"],
                "from_node_id": "not-a-terminal",
                "to_node_id": second_terminal,
            },
        )
        crossing = client.post(
            f"/api/junctions/{junction_id}/crossing", data={"decision": "connected"}
        )
        electrical = client.get(f"/api/analyses/{analysis_id}/electrical-graph")
        exported = client.get(f"/api/analyses/{analysis_id}/export/json")
        bundle = client.get(f"/api/analyses/{analysis_id}/export/bundle")
    assert result["status"] == "complete"
    assert result["stages"][-1]["stage"] == "complete"
    assert added.status_code == 201 and rejected.json()["review_status"] == "rejected"
    assert invalid.status_code == 422
    assert crossing.json()["kind"] == "connected_junction"
    assert electrical.status_code == 200 and electrical.json()["kind"] == "semantic_electrical"
    assert exported.status_code == 200 and exported.json()["schema_version"] == "sldgraph-x/electrical-1"
    assert bundle.status_code == 200 and bundle.headers["content-type"] == "application/zip"


def test_preprocessing_retains_thin_conductor_and_junction_dot() -> None:
    image = Image.new("RGB", (240, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.line((20, 60, 220, 60), fill="black", width=1)
    draw.ellipse((116, 56, 124, 64), fill="black")
    payload = BytesIO()
    image.save(payload, format="PNG")
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "Preservation Test"}).json()
        drawing = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("thin-line.png", payload.getvalue(), "image/png")},
        ).json()
        analysis_id = client.post(f"/api/drawings/{drawing['id']}/analyze").json()[
            "analysis_run_id"
        ]
        artifacts = client.get(f"/api/analyses/{analysis_id}/artifacts").json()
        binary = next(item for item in artifacts if item["type"] == "binary")
        binary_image = Image.open(
            BytesIO(client.get(f"/api/artifacts/{binary['id']}").content)
        ).convert("L")
    assert binary_image.getpixel((20, 60)) < 100
    assert binary_image.getpixel((120, 60)) < 100


def test_missing_controlled_source_records_a_failed_analysis() -> None:
    image = Image.new("RGB", (48, 24), "white")
    payload = BytesIO()
    image.save(payload, format="PNG")
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "Failure Lifecycle"}).json()
        drawing = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("temporary.png", payload.getvalue(), "image/png")},
        ).json()
        controlled_source = Path("var/uploads") / project["id"] / drawing["id"] / "original.png"
        controlled_source.unlink()
        analysis_id = client.post(f"/api/drawings/{drawing['id']}/analyze").json()[
            "analysis_run_id"
        ]
        result = client.get(f"/api/analyses/{analysis_id}").json()
    assert result["status"] == "failed"
    assert result["error_stage"] == "processing"


def test_text_evidence_is_persisted_reviewable_and_summarized() -> None:
    image = Image.new("RGB", (80, 40), "white")
    payload = BytesIO()
    image.save(payload, format="PNG")
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "Text Review"}).json()
        drawing = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": ("text.png", payload.getvalue(), "image/png")},
        ).json()
        analysis_id = client.post(f"/api/drawings/{drawing['id']}/analyze").json()[
            "analysis_run_id"
        ]
        texts = client.get(f"/api/analyses/{analysis_id}/texts").json()
        summary = client.get(f"/api/analyses/{analysis_id}/text-summary").json()
        retrieved = client.get(f"/api/texts/{texts[0]['id']}").json()
        edited = client.patch(
            f"/api/texts/{texts[0]['id']}", data={"value": "FDR-11KV-03", "text_type": "feeder_id"}
        ).json()
        accepted = client.post(f"/api/texts/{texts[0]['id']}/accept").json()
        symbols = client.get(f"/api/analyses/{analysis_id}/symbols").json()
        symbol_summary = client.get(f"/api/analyses/{analysis_id}/symbol-summary").json()
        verified_symbol = client.post(f"/api/symbols/{symbols[0]['id']}/verify").json()
        manual = client.post(
            f"/api/analyses/{analysis_id}/symbols",
            data={
                "drawing_id": drawing["id"],
                "predicted_class": "load",
                "bbox_json": "[0.4, 0.4, 0.6, 0.6]",
            },
        ).json()
        invalid_manual = client.post(
            f"/api/analyses/{analysis_id}/symbols",
            data={
                "drawing_id": drawing["id"],
                "predicted_class": "load",
                "bbox_json": "[0.7, 0.4, 0.6, 0.6]",
            },
        )
    assert texts[0]["raw_text"] == "FDR-11KV-03"
    assert retrieved["raw_text"] == "FDR-11KV-03"
    assert texts[0]["text_type"] == "feeder_id"
    assert summary["recognized"] == 1
    assert edited["engineer_value"] == "FDR-11KV-03"
    assert accepted["review_status"] == "accepted"
    assert symbols[0]["predicted_class"] == "feeder_terminal"
    assert symbol_summary["associated_labels"] == 1
    assert verified_symbol["review_status"] == "verified"
    assert manual["provenance"] == "engineer_added"
    assert invalid_manual.status_code == 422
