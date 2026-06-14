/** 記事カード共通型（API /api/articles のレスポンスに対応） */
export interface Article {
  title: string;
  source: string;
  url: string;
  category_id: string | null;
  reason: string;
  summary: string;
  thumbnail_url: string | null;
  published_at: string | null;
}
