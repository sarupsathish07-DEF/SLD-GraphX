export type Point = { x: number; y: number };
export type Viewport = { x: number; y: number; zoom: number };
export type Size = { width: number; height: number };
export type Bbox = { x: number; y: number; width: number; height: number };
export function normalizedToCanvas(point: Point, master: Size, viewport: Viewport): Point { return { x: point.x * master.width * viewport.zoom + viewport.x, y: point.y * master.height * viewport.zoom + viewport.y }; }
export function canvasToNormalized(point: Point, master: Size, viewport: Viewport): Point { return { x: (point.x - viewport.x) / (master.width * viewport.zoom), y: (point.y - viewport.y) / (master.height * viewport.zoom) }; }
export function normalizedBboxToCanvas(bbox: Bbox, master: Size, viewport: Viewport): Bbox { const origin = normalizedToCanvas(bbox, master, viewport); return { x: origin.x, y: origin.y, width: bbox.width * master.width * viewport.zoom, height: bbox.height * master.height * viewport.zoom }; }
export function fitViewport(master: Size, canvas: Size, padding = 0.08): Viewport { const zoom = Math.min(canvas.width / master.width, canvas.height / master.height) * (1 - padding); return { zoom, x: (canvas.width - master.width * zoom) / 2, y: (canvas.height - master.height * zoom) / 2 }; }
