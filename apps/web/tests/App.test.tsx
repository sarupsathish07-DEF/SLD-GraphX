import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";

describe("command center", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: async () => [] }))));
  it("offers real local project creation", async () => {
    render(<App />);
    expect(await screen.findByText("Create a project")).toBeInTheDocument();
    fireEvent.click(screen.getAllByText("Create project")[0]);
    expect(screen.getByLabelText("Project name")).toBeInTheDocument();
  });
});
