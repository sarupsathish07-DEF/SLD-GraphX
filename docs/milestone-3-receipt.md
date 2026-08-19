# Milestone 3 receipt — local symbol intelligence

Date: 2026-08-19

## VERIFIED

- The product has a bounded ten-class P0 electrical-symbol vocabulary with an adapter boundary, normalized geometry, tile-origin provenance, confidence, engine/model labels, SQLite persistence, and auditable review actions.
- An actual isolated local worker uses project-generated Symbol-v1 data, HOG plus calibrated linear SVM, deterministic busbar geometry, tiled coordinate mapping, and class-aware NMS. Core FastAPI does not import its ML packages.
- The deterministic exporter emits canonical JSON, COCO, YOLO, and tile manifests for 75 drawings / 750 objects, with whole-drawing train/validation/test style A/B/C splits and an unseen style-D holdout.
- Detector training ran from the generated corpus. Its local ignored artifact has SHA-256 `a9f862350459dfd87adeddcceb931c891216debd468f34efed620f30d83d74a2`; the tracked detector manifest records provenance, pins, classes, and constraints.
- Detection, text-to-symbol association, per-symbol persistence, health reporting, explicit worker failure mapping, manual evidence, class correction, accept/reject/verify actions, and drawing-overlay review are integrated in the API and workspace.
- Real smoke and product-path smoke ran locally. The latter completed `ingestion → inspection → rendering → preprocessing → ocr → text_normalization → text_semantics → symbol_detection → text_symbol_association → complete`, persisted 10 symbols, and associated 10 labels.
- Controlled deployment-worker benchmark completed: test 70/21/20 TP/FP/FN and 0.7778 component semantic match; style holdout 76/47/44 and 0.6333. mAP values are intentionally reported as unavailable rather than fabricated.

## PARTIAL

- The model is HOG/SVM/joblib rather than ONNX/OpenVINO, and the worker starts per request. It is an isolated working local runtime, not a warmed inference service.
- Visual browser/screenshot QA remains partial because the in-app browser binding previously failed before page inspection. Unit/UI tests, lint, and production build validate the rendered code path but are not a visual acceptance substitute.
- Controlled degradation is measured on one parent drawing per condition. A legally verified public/real microset is not registered and real validation is not run.

## NOT IMPLEMENTED

- Conductor, junction, terminal, and bus connectivity reconstruction; electrical graph assembly from uploads; source/feeder reasoning; switch-state connectivity; DXF/vector evidence; graph export for uploaded drawings; power flow; fault analysis; IEC compliance claims.

## Checkpoint

The M3 code, generator, manifests, documents, and regression evidence are committed as one coherent checkpoint. The Git handoff reports the pushed commit identity.
