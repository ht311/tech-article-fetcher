"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { IcoHome, IcoArchive, IcoStats, IcoSettings } from "./icons/TabIcons";

const TABS = [
  { href: "/",          label: "ホーム",   Icon: IcoHome },
  { href: "/articles/", label: "過去記事", Icon: IcoArchive },
  { href: "/stats/",    label: "統計",     Icon: IcoStats },
  { href: "/settings/", label: "設定",     Icon: IcoSettings },
] as const;

const ACCENT = "#b1402e";
const SUBTLE = "#9a9183";

export function BottomTabBar() {
  const pathname = usePathname();

  return (
    <nav
      style={{
        flexShrink: 0,
        display: "flex",
        background: "var(--color-press-surface)",
        borderTop: "1px solid var(--color-press-border)",
        paddingBottom: "env(safe-area-inset-bottom, 0px)",
      }}
    >
      {TABS.map(({ href, label, Icon }) => {
        const active =
          href === "/"
            ? pathname === "/"
            : pathname === href || pathname.startsWith(href.replace(/\/$/, ""));
        return (
          <Link
            key={href}
            href={href}
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 4,
              paddingTop: 10,
              paddingBottom: 10,
              color: active ? ACCENT : SUBTLE,
              textDecoration: "none",
            }}
          >
            <Icon size={22} sw={active ? 2.1 : 1.7} />
            <span
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: 9.5,
                fontWeight: active ? 700 : 400,
                letterSpacing: "0.01em",
              }}
            >
              {label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
