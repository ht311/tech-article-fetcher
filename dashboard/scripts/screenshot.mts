import { chromium } from "@playwright/test";
import { readFileSync } from "fs";
import { mkdirSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixturesDir = resolve(__dirname, "fixtures");
const outputDir = resolve(__dirname, "../../docs/screenshots");

mkdirSync(outputDir, { recursive: true });

function loadFixture(name: string): string {
  return readFileSync(resolve(fixturesDir, `${name}.json`), "utf-8");
}

const TODAY = "2026-05-01";

const routes: { path: string; name: string; apiMocks: Record<string, string> }[] = [
  {
    path: "/",
    name: "home",
    apiMocks: {
      "/api/stats": loadFixture("stats"),
      [`/api/articles?from=${TODAY}&to=${TODAY}`]: JSON.stringify({
        dates: [TODAY],
        articles: { [TODAY]: JSON.parse(loadFixture("articles")).articles[TODAY] },
      }),
    },
  },
  {
    path: "/articles/",
    name: "articles",
    apiMocks: {
      "/api/articles": loadFixture("articles"),
    },
  },
  {
    path: "/stats/",
    name: "stats",
    apiMocks: {
      "/api/stats": loadFixture("stats"),
    },
  },
  {
    path: "/settings/",
    name: "settings",
    apiMocks: {
      "/api/settings": loadFixture("settings"),
      "/api/settings/defaults": loadFixture("settings"),
    },
  },
];

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });

  for (const route of routes) {
    const page = await context.newPage();

    // Intercept API calls and return fixture data
    await page.route("**/api/**", (r) => {
      const url = new URL(r.request().url());
      const key = url.pathname + url.search;
      // Try exact match, then pathname-only match
      const body = route.apiMocks[key] ?? route.apiMocks[url.pathname];
      if (body !== undefined) {
        r.fulfill({ status: 200, contentType: "application/json", body });
      } else {
        r.fulfill({ status: 200, contentType: "application/json", body: "null" });
      }
    });

    await page.goto(`${BASE_URL}${route.path}`);
    // Wait for network idle so charts / data finish rendering
    await page.waitForLoadState("networkidle");
    // Extra small delay for CSS transitions
    await page.waitForTimeout(300);

    const outPath = resolve(outputDir, `${route.name}.png`);
    await page.screenshot({ path: outPath, fullPage: false });
    console.log(`  saved: ${outPath}`);
    await page.close();
  }

  await browser.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
