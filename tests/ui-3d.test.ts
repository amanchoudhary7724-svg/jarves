import { test, expect } from "@playwright/test";

const INDEX_URL = "file:///C:/Users/soura/Documents/Default%20Project/jarvis/index.html";

test.describe("Jarvis UI visual & functional checks", () => {
  test("page loads and renders key sections", async ({ page }) => {
    await page.goto(INDEX_URL, { waitUntil: "load" });
    await expect(page.locator(".side-panel")).toBeVisible();
    await expect(page.locator(".center-stage")).toBeVisible();
    await expect(page.locator(".right-panel")).toBeVisible();
  });

  test("avatar has an idle animation", async ({ page }) => {
    await page.goto(INDEX_URL, { waitUntil: "load" });
    const avatar = page.locator("#avatarImg");
    await expect(avatar).toBeVisible();
    const animationName = await avatar.evaluate((el) =>
      window.getComputedStyle(el).animationName
    );
    expect(animationName).toContain("idleBreathing");
  });

  test("local greeting sends and renders a reply", async ({ page }) => {
    await page.goto(INDEX_URL, { waitUntil: "load" });
    await page.locator("#textInput").fill("kaise ho");
    await page.locator("#sendBtn").click();
    await expect(page.locator(".chat-msg.user").last()).toContainText("kaise ho");
    await expect(page.locator(".chat-msg.jarvis").last()).toContainText("Main bilkul fit hoon Boss");
  });

  test("screenshot taken in desktop and mobile viewports", async ({ page }) => {
    // Desktop screenshot
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(INDEX_URL, { waitUntil: "load" });
    await page.screenshot({ path: "../screenshots/jarvis-desktop.png", fullPage: true });

    // Mobile screenshot
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(INDEX_URL, { waitUntil: "load" });
    await page.screenshot({ path: "../screenshots/jarvis-mobile.png", fullPage: true });
  });
});
