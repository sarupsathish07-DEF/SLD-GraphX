# Product specification

SLDGraph-X is intended to convert SLD evidence into a reviewable canonical electrical graph. P0 will accept PNG, JPEG and raster PDF; it will preserve raw evidence, construct terminal-aware connectivity, identify sources and feeders, rank topology-critical uncertainty, and export JSON/CSV.

The product is local-first. A user reviews consequential uncertainty rather than trusting silent topology guesses. DXF/vector PDF, OCR, symbol detection, and scenario refinement are layered additions; a graph connectivity toggle is not power-flow simulation.
