import { expect, test } from "@playwright/test";

const output = "../../../artifacts/screenshots/bootstrap";

test("captures the Bootstrap workspace at 1920x1080", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("TOPOLOGY EXPLORER")).toBeVisible();
  await expect(page.locator(".sld-canvas svg")).toBeVisible();
  await expect(page.locator(".flow-canvas .react-flow")).toBeVisible();
  await page.screenshot({ path: `${output}/workspace-1920x1080.png`, fullPage: true });
  await page.locator(".sld-canvas").screenshot({ path: `${output}/reconstructed-svg.png` });
  await page.locator(".flow-canvas").screenshot({ path: `${output}/topology-react-flow.png` });
});
