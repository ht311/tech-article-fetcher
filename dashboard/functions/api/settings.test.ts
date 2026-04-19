import { describe, it, expect } from "vitest";
import { validateSettings } from "./settings";

describe("validateSettings", () => {
  it("returns null for valid v1 settings", () => {
    expect(validateSettings({ max_per_category: 3 })).toBeNull();
  });

  it("rejects max_per_category out of range", () => {
    expect(validateSettings({ max_per_category: 0 })).toMatch(/max_per_category/);
    expect(validateSettings({ max_per_category: 6 })).toMatch(/max_per_category/);
  });

  it("rejects article_fetch_hours out of range", () => {
    expect(validateSettings({ article_fetch_hours: 0 })).toMatch(/article_fetch_hours/);
    expect(validateSettings({ article_fetch_hours: 169 })).toMatch(/article_fetch_hours/);
  });

  it("accepts article_fetch_hours in range", () => {
    expect(validateSettings({ article_fetch_hours: 1 })).toBeNull();
    expect(validateSettings({ article_fetch_hours: 168 })).toBeNull();
  });

  it("rejects gemini_max_input_per_category out of range", () => {
    expect(validateSettings({ gemini_max_input_per_category: 4 })).toMatch(/gemini_max_input_per_category/);
    expect(validateSettings({ gemini_max_input_per_category: 51 })).toMatch(/gemini_max_input_per_category/);
  });

  it("rejects duplicate source names", () => {
    const sources = [
      { name: "Zenn", type: "rss" as const, url: "https://zenn.dev/feed", enabled: true },
      { name: "Zenn", type: "rss" as const, url: "https://zenn.dev/feed", enabled: true },
    ];
    expect(validateSettings({ sources })).toMatch(/Duplicate source name/);
  });

  it("rejects invalid source type", () => {
    const sources = [{ name: "HN", type: "hackernews" as never, enabled: true }];
    expect(validateSettings({ sources })).toMatch(/Invalid source type/);
  });

  it("rejects rss source without url", () => {
    const sources = [{ name: "Zenn", type: "rss" as const, enabled: true }];
    expect(validateSettings({ sources })).toMatch(/requires a url/);
  });

  it("accepts rss source with url", () => {
    const sources = [{ name: "Zenn", type: "rss" as const, url: "https://zenn.dev/feed", enabled: true }];
    expect(validateSettings({ sources })).toBeNull();
  });

  it("rejects duplicate category ids", () => {
    const category_defs = [
      { id: "backend", name: "バックエンド", keywords: [], enabled: true, order: 0 },
      { id: "backend", name: "Backend", keywords: [], enabled: true, order: 1 },
    ];
    expect(validateSettings({ category_defs })).toMatch(/Duplicate category id/);
  });

  it("accepts valid category_defs", () => {
    const category_defs = [
      { id: "backend", name: "バックエンド", keywords: ["java"], enabled: true, order: 0 },
      { id: "frontend", name: "フロントエンド", keywords: ["react"], enabled: true, order: 1 },
    ];
    expect(validateSettings({ category_defs })).toBeNull();
  });
});
