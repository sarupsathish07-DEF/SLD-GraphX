# Symbol detector training and local deployment

`scripts/bootstrap_detector.ps1` creates two isolated Python 3.10 environments: `.venv-sldgraphx-detector-train` for corpus training and `.venv-sldgraphx-detector` for product inference. Both pin NumPy 1.26.4, OpenCV headless 4.10.0.84, scikit-learn 1.5.2, and Pydantic 2.13.4, then run `pip check`. Core FastAPI and the OCR environment remain free of these detector dependencies.

The tracked generator produces Symbol-v1 then `scripts/train_symbol_detector.py` learns a calibrated `LinearSVC` over project-owned OpenCV HOG 64×64 features. Training has fixed seed 42, balanced classes, C=1.0, and four deterministic box jitters per training crop. Busbar does not enter the classifier: the worker uses a documented deterministic elongated-line geometry route. The local joblib payload is deliberately ignored; its SHA-256, size, dataset-manifest SHA-256, runtime pins, taxonomy, and limits are tracked in `models/detector/manifest.json`.

The trained crop-validation macro F1 was 1.0 across 81 controlled synthetic validation crops. This is a classification sanity check, not an object-detection metric. Deployment is an actual JSON-lines worker invoked only with a local model path. It has no model download or cloud fallback. ONNX and OpenVINO packaging were not implemented or evaluated; this is a classical local deployment rather than an ONNX/OpenVINO claim.

The recorded package metadata lists scikit-learn under BSD-3-Clause and OpenCV under Apache-2.0; NumPy's distribution carries bundled-component notices. This repository record is not legal advice. Ultralytics was deliberately not used because its AGPL option requires a separate licensing decision for this project.
