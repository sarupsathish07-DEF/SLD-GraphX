# Physical topology reconstruction

M4 turns persisted symbol/text evidence and a local rendered page into a reviewable undirected physical graph. The pipeline protects symbol and text boxes, traces horizontal/vertical morphology plus strong angled lines, thins evidence with Zhang-Suen, extracts long-line and detected busbars, and preserves raw traces independently of selected edges.

Connected junctions require skeleton branching plus compact dark-dot raster evidence. Intersections without that evidence are retained as ambiguous crossovers for review; they are not silently treated as electrical joins. Symbol templates produce IN, OUT, or ATTACH terminals. Endpoint snapping uses each symbol's normalized diagonal to scale its tolerance. Candidate edges retain visual continuity, endpoint distance, orientation, terminal, junction, and structural scores. Duplicate terminal pairs keep the strongest trace. Orphans, unusual device degree, weak edges, and masked gap bridges are review issues. A gap bridge is only proposed when two one-sided terminal traces are close and collinear, and always remains pending.

The API persists and returns raw evidence, candidates, physical graph, issues, crossing decisions, and immutable engineer review actions. Manual edges require two distinct terminals belonging to the requested drawing/analysis. The React workspace overlays traces, buses, junctions, and physical edges on the original SLD and shows the same terminal graph alongside it.

This module is deliberately pre-semantic. It does not assign sources/feeders, choose switch-state connectivity, direction, energized status, flow, or source-to-feeder paths.

M4R adds adaptive box insets and terminal corridors, multi-scale line evidence, terminal-to-segment projection, short corridor scans, endpoint-led component clustering, bus-rooted T branches, and T-versus-X distinction. Review-state candidates remain auditable; an undotted X is never promoted to a connection merely to improve recall. See the [repair log](topology-repair-log.md) and [M4R receipt](milestone-4r-receipt.md) for frozen evidence.
