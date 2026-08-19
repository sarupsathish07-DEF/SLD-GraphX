import { describe, expect, it } from "vitest";
import { canvasToNormalized, fitViewport, normalizedBboxToCanvas, normalizedToCanvas } from "../src/lib/geometry";

describe("normalized canvas coordinates", () => {
  it("round trips a zoomed and panned point", () => { const master = { width: 6842, height: 4410 }; const viewport = { x: 180, y: 40, zoom: .2 }; const point = { x: .45, y: .8 }; expect(canvasToNormalized(normalizedToCanvas(point, master, viewport), master, viewport)).toEqual(point); });
  it("fits differing viewport proportions", () => { const fit = fitViewport({ width: 6842, height: 4410 }, { width: 1536, height: 864 }); expect(fit.zoom).toBeGreaterThan(0); expect(fit.x).toBeGreaterThanOrEqual(0); });
  it("maps normalized bounding boxes with pan and zoom", () => { expect(normalizedBboxToCanvas({ x: .1, y: .2, width: .3, height: .4 }, { width: 1000, height: 500 }, { x: 10, y: 20, zoom: .5 })).toEqual({ x: 60, y: 70, width: 150, height: 100 }); });
});
