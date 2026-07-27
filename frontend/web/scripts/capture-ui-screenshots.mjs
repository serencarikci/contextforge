import { chromium } from "@playwright/test";
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import os from "node:os";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(__dirname, "../../../docs/screenshots/ui");
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001";
const HOME = os.homedir();

function resolveBrowserExecutable() {
  if (process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE) {
    return process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
  }
  const candidates = [
    path.join(
      HOME,
      "Library/Caches/ms-playwright/chromium-1179/chrome-mac/Chromium.app/Contents/MacOS/Chromium",
    ),
    path.join(
      HOME,
      "Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell",
    ),
    path.join(
      HOME,
      "Library/Caches/ms-playwright/chromium_headless_shell-1179/chrome-mac/headless_shell",
    ),
  ];
  return candidates.find((candidate) => existsSync(candidate));
}

const ADMIN = {
  userId: "5edca01c-b054-52c5-b31a-c5374d34f012",
  organizationId: "e4ada683-9d59-5d55-b284-e75fafc0e52c",
  email: "admin@contextforge.local",
  displayName: "Dev Admin",
};

const PERMISSIONS = [
  "organization:read",
  "organization:update",
  "organization:manage_members",
  "user:read",
  "user:manage",
  "role:read",
  "role:manage",
  "customer:create",
  "customer:read",
  "customer:update",
  "customer:archive",
  "project:create",
  "project:read",
  "project:update",
  "project:archive",
  "project:manage_members",
  "knowledge_space:create",
  "knowledge_space:read",
  "knowledge_space:update",
  "knowledge_space:archive",
  "knowledge_space:manage_members",
  "document:create",
  "document:read",
  "document:update",
  "document:delete",
  "rag:query",
  "audit:read",
  "chat:use",
  "chat:manage",
  "admin:dashboard",
  "admin:users",
  "admin:organizations",
  "admin:roles",
  "admin:knowledge_spaces",
  "admin:documents",
  "admin:ingestion",
  "admin:audit",
  "admin:usage",
  "admin:prompts",
  "admin:llm",
  "admin:settings",
  "admin:ops",
  "admin:retention",
];

const SHOTS = [
  { name: "01-login", path: "/login", auth: false },
  { name: "02-forgot-password", path: "/forgot-password", auth: false },
  { name: "03-reset-password", path: "/reset-password", auth: false },
  { name: "04-session-expired", path: "/session-expired", auth: false },
  { name: "05-unauthorized", path: "/unauthorized", auth: false },
  { name: "06-chat", path: "/chat", auth: true },
  {
    name: "07-chat-conversation",
    path: "/chat/79e2bdb1-d61f-4e7f-b1d9-8b4cd11a99c5",
    auth: true,
  },
  { name: "08-documents", path: "/documents", auth: true },
  { name: "09-documents-upload", path: "/documents/upload", auth: true },
  { name: "10-knowledge-spaces", path: "/knowledge-spaces", auth: true },
  { name: "11-knowledge-spaces-new", path: "/knowledge-spaces/new", auth: true },
  {
    name: "12-knowledge-space-detail",
    path: "/knowledge-spaces/99d63d81-8c30-5408-9f24-c350f341e224",
    auth: true,
  },
  { name: "13-customers", path: "/customers", auth: true },
  { name: "14-projects", path: "/projects", auth: true },
  { name: "15-analytics", path: "/analytics", auth: true },
  { name: "16-system", path: "/system", auth: true },
  { name: "17-settings", path: "/settings", auth: true },
  { name: "18-admin-dashboard", path: "/admin", auth: true },
  { name: "19-admin-users", path: "/admin/users", auth: true },
  { name: "20-admin-organizations", path: "/admin/organizations", auth: true },
  { name: "21-admin-roles", path: "/admin/roles", auth: true },
  { name: "22-admin-prompts", path: "/admin/prompts", auth: true },
  { name: "23-admin-llm", path: "/admin/llm-providers", auth: true },
  { name: "24-admin-feature-flags", path: "/admin/feature-flags", auth: true },
  { name: "25-admin-audit", path: "/admin/audit", auth: true },
  { name: "26-admin-retention", path: "/admin/retention", auth: true },
  { name: "27-admin-settings", path: "/admin/settings", auth: true },
];

async function seedAdminSession(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.evaluate(
    ({ admin, permissions }) => {
      const expiresAt = Date.now() + 8 * 60 * 60 * 1000;
      localStorage.setItem(
        "cf-session",
        JSON.stringify({
          state: {
            userId: admin.userId,
            organizationId: admin.organizationId,
            projectId: null,
            knowledgeSpaceId: null,
            email: admin.email,
            displayName: admin.displayName,
            expiresAt,
            permissions,
          },
          version: 0,
        }),
      );
      document.cookie = "cf_session=1; Path=/; SameSite=Lax";
    },
    { admin: ADMIN, permissions: PERMISSIONS },
  );
}

async function clearSession(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.removeItem("cf-session");
    document.cookie = "cf_session=; Path=/; Max-Age=0; SameSite=Lax";
  });
}

async function dismissOverlays(page) {
  await page.evaluate(() => {
    try {
      localStorage.setItem(
        "cf-ui",
        JSON.stringify({ state: { sidebarCollapsed: false, notifications: [] }, version: 0 }),
      );
    } catch {
    }
  });
  await page.keyboard.press("Escape").catch(() => {});
  await page.locator('[data-state="open"].fixed.inset-0').waitFor({ state: "hidden", timeout: 1500 }).catch(() => {});
}

async function shot(page, name) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await dismissOverlays(page);
  await page.waitForTimeout(600);
  await page.screenshot({ path: file, fullPage: true });
  console.log("saved", file);
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const executablePath = resolveBrowserExecutable();
  const browser = await chromium.launch({
    headless: true,
    ...(executablePath ? { executablePath } : {}),
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  let authed = false;

  for (const item of SHOTS) {
    try {
      if (item.auth) {
        if (!authed) {
          await seedAdminSession(page);
          authed = true;
        }
      } else {
        await clearSession(page);
        authed = false;
      }

      await page.goto(`${BASE}${item.path}`, {
        waitUntil: "networkidle",
        timeout: 60_000,
      });
      await dismissOverlays(page);
      if (item.setup) {
        await item.setup(page);
      }
      await shot(page, item.name);
    } catch (error) {
      console.error("failed", item.name, error);
      try {
        await shot(page, `${item.name}-error`);
      } catch {
      }
    }
  }

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
