import { expect, test } from "@playwright/test";

test("login page renders", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: /ContextForge|Sign in|oturum/i })).toBeVisible({
    timeout: 15_000,
  });
});
