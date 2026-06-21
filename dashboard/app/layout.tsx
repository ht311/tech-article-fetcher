import type { Metadata } from "next";
import { Geist_Mono, Noto_Sans_JP, Newsreader } from "next/font/google";
import { BottomTabBar } from "./components/BottomTabBar";
import "./globals.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-newsreader",
  display: "swap",
});

const notoSansJP = Noto_Sans_JP({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-noto-sans-jp",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});

export const metadata: Metadata = {
  title: "Tech Dispatch",
  description: "tech-article-fetcher ダッシュボード",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="ja"
      className={`${newsreader.variable} ${notoSansJP.variable} ${geistMono.variable} h-full`}
    >
      <body className="h-dvh flex flex-col" style={{ background: "var(--color-press-bg)" }}>
        <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
          {children}
        </main>
        <BottomTabBar />
      </body>
    </html>
  );
}
