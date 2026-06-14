import { categoryPlaceholderBg } from "../lib/categoryColors";
import type { Article } from "../lib/types";

interface Props {
  article: Article;
  rating?: "good" | "bad" | null;
  onRate?: (action: "good" | "bad") => void;
}

export function ArticleCard({ article: a, rating, onRate }: Props) {
  return (
    <a
      href={a.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden hover:border-blue-300 hover:shadow-sm transition-all active:opacity-80"
    >
      {/* サムネイル (OGP 標準比 1.91:1) */}
      <div className="w-full aspect-[1.91/1] overflow-hidden shrink-0">
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
            <span className="text-3xl select-none">📄</span>
          </div>
        )}
      </div>

      {/* テキスト */}
      <div className="flex-1 p-3 min-w-0">
        <p className="text-sm font-semibold leading-snug line-clamp-2 text-gray-900">
          {a.title}
        </p>

        {a.summary && (
          <p className="text-xs text-gray-500 mt-1 leading-relaxed line-clamp-2">
            {a.summary}
          </p>
        )}

        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <span className="text-xs text-gray-400">{a.source}</span>
          {a.reason && (
            <span className="text-xs text-gray-400 truncate max-w-[12rem]">
              🏷 {a.reason}
            </span>
          )}
        </div>

        {onRate && (
          <div className="flex gap-2 mt-3">
            <button
              type="button"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRate("good"); }}
              className={`flex-1 text-sm py-1 rounded-lg border transition-colors ${rating === "good" ? "bg-green-100 border-green-400 text-green-700 font-semibold" : "border-gray-200 text-gray-400 hover:bg-green-50 hover:border-green-300 hover:text-green-600"}`}
            >
              👍
            </button>
            <button
              type="button"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRate("bad"); }}
              className={`flex-1 text-sm py-1 rounded-lg border transition-colors ${rating === "bad" ? "bg-red-100 border-red-400 text-red-700 font-semibold" : "border-gray-200 text-gray-400 hover:bg-red-50 hover:border-red-300 hover:text-red-600"}`}
            >
              👎
            </button>
          </div>
        )}
      </div>
    </a>
  );
}
