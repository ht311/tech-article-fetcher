type IconProps = { size?: number; sw?: number };

export const IcoHome = ({ size = 22, sw = 1.8 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true"
    stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9.5L12 3l9 6.5V21a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z"/>
    <path d="M9 22V12h6v10"/>
  </svg>
);

export const IcoArchive = ({ size = 22, sw = 1.8 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true"
    stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="5" rx="1"/>
    <path d="M4 9v11a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V9"/>
    <line x1="9" y1="14" x2="15" y2="14"/>
  </svg>
);

export const IcoStats = ({ size = 22, sw = 1.8 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true"
    stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/>
    <line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6"  y1="20" x2="6"  y2="14"/>
    <line x1="2"  y1="20" x2="22" y2="20"/>
  </svg>
);

export const IcoSettings = ({ size = 22, sw = 1.8 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true"
    stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06
             a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09
             A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83
             l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09
             A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83
             l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09
             a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83
             l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09
             a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
);
