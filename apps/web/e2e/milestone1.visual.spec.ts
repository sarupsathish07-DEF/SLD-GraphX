import { expect, test } from "@playwright/test";

const output = "../../../artifacts/screenshots/milestone-1";
// A deliberately tiny valid PNG; the real upload endpoint still receives it.
const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLNeQAAAABJRU5ErkJggg==", "base64");

test("creates, imports, preprocesses, and reopens a local drawing", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Command center")).toBeVisible();
  await page.screenshot({ path: `${output}/01-command-center.png` });
  await page.getByRole("button", { name: "New project" }).click();
  await page.getByLabel("Project name").fill(`E2E substation ${Date.now()}`);
  await page.getByRole("button", { name: "Create project", exact: true }).click();
  await expect(page.getByText("Bring in a drawing")).toBeVisible();
  await page.getByLabel("Choose drawing").setInputFiles({ name: "sldforge-radial.png", mimeType: "image/png", buffer: png });
  await page.getByRole("button", { name: "Upload drawing" }).click();
  await expect(page.getByText("Document inspection")).toBeVisible();
  await page.screenshot({ path: `${output}/02-import-studio.png` });
  await page.getByRole("button", { name: "Analyze drawing" }).click();
  await expect(page.getByText("Analysis progress")).toBeVisible();
  await page.screenshot({ path: `${output}/03-analysis-progress.png` });
  await expect(page.getByText("Intelligence workspace")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByAltText("Uploaded electrical drawing")).toBeVisible();
  await expect(page.getByText("Drawing inspector")).toBeVisible();
  await page.screenshot({ path: `${output}/04-intelligence-workspace.png` });
  await page.getByTitle("Demo fixture").click();
  await expect(page.getByText("Graph Explorer")).toBeVisible();
  await page.screenshot({ path: `${output}/05-graph-explorer.png` });
});
