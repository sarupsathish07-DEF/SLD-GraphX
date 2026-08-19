# Data provenance

User uploads remain local in controlled `var/uploads/<project>/<drawing>/` storage. The database stores identifiers, sanitized filename, MIME type, SHA-256, size, inspection evidence, and safe relative artifact references; it never stores image blobs or exposes local paths to the browser.

Milestone 1 render/preprocessing artifacts are stored under controlled `var/renders/<analysis-run>/` storage. Each has an opaque artifact ID, SHA-256, MIME type, relative path, page, dimensions, and generation configuration. The artifact API validates the resolved path remains under `var/` before serving it.

SLDForge samples are project-generated controlled synthetic data marked `synthetic_ground_truth`. Their manifests identify seed, topology, canonical equipment/terminals/connections/switch states, rendered text, and exact source-to-feeder paths. They are not real measurements or a claim about field generalization.
