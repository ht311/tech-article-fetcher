import { describe, it, expect } from "vitest";
import { groupByCategory } from "./groupByCategory";
import type { Article } from "./types";

const makeArticle = (category_id: string | null, title = "test"): Article => ({
  title,
  source: "src",
  url: "https://example.com",
  category_id,
  reason: "",
  summary: "",
  thumbnail_url: null,
  published_at: null,
});

const categories = [
  { id: "backend", name: "バックエンド" },
  { id: "frontend", name: "フロントエンド" },
  { id: "aws", name: "AWS" },
];

describe("groupByCategory", () => {
  it("グループがカテゴリ定義の順番通りに並ぶ", () => {
    const articles = [
      makeArticle("frontend", "front-1"),
      makeArticle("backend", "back-1"),
      makeArticle("aws", "aws-1"),
    ];
    const groups = groupByCategory(articles, categories);
    expect(groups.map((g) => g.id)).toEqual(["backend", "frontend", "aws"]);
  });

  it("空配列は空を返す", () => {
    expect(groupByCategory([], categories)).toEqual([]);
  });

  it("記事が無いカテゴリはグループを返さない", () => {
    const articles = [makeArticle("backend")];
    const groups = groupByCategory(articles, categories);
    expect(groups.map((g) => g.id)).toEqual(["backend"]);
  });

  it("category_id が null の記事は末尾の「その他」グループに入る", () => {
    const articles = [makeArticle("backend"), makeArticle(null)];
    const groups = groupByCategory(articles, categories);
    const ids = groups.map((g) => g.id);
    expect(ids[0]).toBe("backend");
    expect(ids[ids.length - 1]).toBe("others");
  });

  it("定義に無い category_id の記事も末尾の「その他」グループに入る", () => {
    const articles = [makeArticle("backend"), makeArticle("unknown")];
    const groups = groupByCategory(articles, categories);
    const last = groups[groups.length - 1];
    expect(last.id).toBe("others");
    expect(last.articles[0].category_id).toBe("unknown");
  });

  it("カテゴリ定義が空のときはすべて「その他」グループに入る", () => {
    const articles = [makeArticle("backend"), makeArticle(null)];
    const groups = groupByCategory(articles, []);
    expect(groups).toHaveLength(1);
    expect(groups[0].id).toBe("others");
    expect(groups[0].articles).toHaveLength(2);
  });

  it("各グループ内の記事順序は入力順を保持する", () => {
    const articles = [
      makeArticle("backend", "b1"),
      makeArticle("backend", "b2"),
      makeArticle("backend", "b3"),
    ];
    const groups = groupByCategory(articles, categories);
    expect(groups[0].articles.map((a) => a.title)).toEqual(["b1", "b2", "b3"]);
  });
});
