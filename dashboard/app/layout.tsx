import type { Metadata } from "next";
import { Geist, Noto_Sans_JP } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });
const notoSansJP = Noto_Sans_JP({ subsets: ["latin"], weight: ["400", "500", "700"] });

export const metadata: Metadata = {
  title: "Tech Article Dashboard",
  description: "tech-article-fetcher 管理ダッシュボード",
};

const NAV_LINKS = [
  { href: "/", label: "ホーム" },
  { href: "/articles/", label: "過去記事" },
  { href: "/stats/", label: "統計" },
  { href: "/settings/", label: "設定" },
];

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ja" className={`${geist.className} ${notoSansJP.className} h-full`}>
      <body className="min-h-full flex flex-col bg-gray-50 text-gray-900">
        <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-6">
          <span className="font-semibold text-sm">📰 Article Dashboard</span>
          <nav className="flex gap-4">
            {NAV_LINKS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                {label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="flex-1 px-6 py-6 max-w-5xl mx-auto w-full">
          {children}
        </main>
      </body>
    </html>
  );
}
