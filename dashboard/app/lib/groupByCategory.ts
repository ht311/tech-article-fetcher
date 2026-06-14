import type { Article } from "./types";
import type { CategoryMeta } from "./useCategories";

export interface CategoryGroup {
  id: string;
  name: string;
  articles: Article[];
}

/**
 * 記事をカテゴリ別グループに分類する。
 * - category_defs の順番通りにグループを並べる
 * - 定義に無い / null のカテゴリは末尾の「その他」グループへ
 * - 記事が1件も無いカテゴリはグループを返さない
 */
export function groupByCategory(
  articles: Article[],
  categories: CategoryMeta[],
): CategoryGroup[] {
  const knownIds = new Set(categories.map((c) => c.id));

  // カテゴリ定義順でバケットを初期化
  const buckets = new Map<string, Article[]>();
  for (const cat of categories) {
    buckets.set(cat.id, []);
  }
  const others: Article[] = [];

  for (const article of articles) {
    const id = article.category_id;
    if (id && knownIds.has(id)) {
      buckets.get(id)?.push(article);
    } else {
      others.push(article);
    }
  }

  const groups: CategoryGroup[] = [];

  for (const cat of categories) {
    const arts = buckets.get(cat.id) ?? [];
    if (arts.length > 0) {
      groups.push({ id: cat.id, name: cat.name, articles: arts });
    }
  }

  if (others.length > 0) {
    groups.push({ id: "others", name: "その他", articles: others });
  }

  return groups;
}
