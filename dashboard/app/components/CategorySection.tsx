import { categoryBadgeClass } from "../lib/categoryColors";
import type { Article } from "../lib/types";
import { ArticleCard } from "./ArticleCard";

interface Props {
  id: string;
  name: string;
  articles: Article[];
}

export function CategorySection({ id, name, articles }: Props) {
  if (articles.length === 0) return null;

  return (
    <section>
      {/* カテゴリ見出し */}
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`text-xs font-semibold px-2 py-0.5 rounded-full ${categoryBadgeClass(id)}`}
        >
          {name}
        </span>
        <span className="text-xs text-gray-400">{articles.length}件</span>
      </div>

      {/* 記事カードグリッド（スマホ1列 / デスクトップ2列） */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
        {articles.map((a) => (
          <ArticleCard key={a.url} article={a} />
        ))}
      </div>
    </section>
  );
}
