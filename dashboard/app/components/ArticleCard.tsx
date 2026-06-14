import { categoryPlaceholderBg } from "../lib/categoryColors";
import type { Article } from "../lib/types";

interface Props {
  article: Article;
}

export function ArticleCard({ article: a }: Props) {
  return (
    <a
      href={a.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex gap-3 bg-white border border-gray-200 rounded-xl p-3 hover:border-blue-300 hover:shadow-sm transition-all active:opacity-80"
    >
      {/* サムネイル */}
      <div className="shrink-0 w-20 h-14 sm:w-24 sm:h-16 rounded-lg overflow-hidden">
        {a.thumbnail_url ? (
          // biome-ignore lint/performance/noImgElement: thumbnail URLs are external and domain-unpredictable
          <img
            src={a.thumbnail_url}
            alt=""
            className="w-full h-full object-cover"
          />
        ) : (
          <div
            className={`w-full h-full flex items-center justify-center ${categoryPlaceholderBg(a.category_id)}`}
          >
            <span className="text-xl select-none">📄</span>
          </div>
        )}
      </div>

      {/* テキスト */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold leading-snug line-clamp-2 text-gray-900">
          {a.title}
        </p>

        {a.summary && (
          <p className="text-xs text-gray-500 mt-1 leading-relaxed line-clamp-3">
            {a.summary}
          </p>
        )}

        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          <span className="text-xs text-gray-400">{a.source}</span>
          {a.reason && (
            <span className="text-xs text-gray-400 truncate max-w-[12rem]">
              🏷 {a.reason}
            </span>
          )}
        </div>
      </div>
    </a>
  );
}
