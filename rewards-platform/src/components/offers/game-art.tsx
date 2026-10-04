import { useId } from "react";
import type { ArtVariant } from "@/lib/offers/types";

/**
 * Original, genre-level illustrations for ILLUSTRATIVE offers. They deliberately depict no real
 * game, character or brand (DECISIONS D-019). When real catalog data exists, provider-supplied
 * artwork replaces these only where the provider's terms permit its display.
 */
export function GameArt({ variant, className }: { variant: ArtVariant; className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg
      viewBox="0 0 320 180"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {ART[variant](id)}
    </svg>
  );
}

const ART: Record<ArtVariant, (id: string) => React.ReactNode> = {
  city: (id) => (
    <>
      <defs>
        <linearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8fd3fe" />
          <stop offset="1" stopColor="#c9b8ff" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill={`url(#${id}-sky)`} />
      <circle cx="252" cy="52" r="24" fill="#fff4c2" />
      <g fill="#4338ca">
        <rect x="18" y="86" width="42" height="94" rx="4" />
        <rect x="66" y="58" width="36" height="122" rx="4" />
        <rect x="108" y="96" width="48" height="84" rx="4" />
        <rect x="162" y="70" width="34" height="110" rx="4" />
        <rect x="202" y="104" width="56" height="76" rx="4" />
        <rect x="264" y="82" width="40" height="98" rx="4" />
      </g>
      <g fill="#c7d2fe" opacity="0.9">
        {[0, 1, 2, 3, 4].map((r) =>
          [0, 1].map((c) => (
            <rect key={`a${r}${c}`} x={74 + c * 14} y={70 + r * 18} width="7" height="9" rx="1.5" />
          )),
        )}
        {[0, 1, 2, 3].map((r) =>
          [0, 1].map((c) => (
            <rect
              key={`b${r}${c}`}
              x={169 + c * 13}
              y={82 + r * 20}
              width="7"
              height="9"
              rx="1.5"
            />
          )),
        )}
        {[0, 1, 2].map((r) =>
          [0, 1, 2].map((c) => (
            <rect
              key={`c${r}${c}`}
              x={212 + c * 14}
              y={116 + r * 18}
              width="7"
              height="9"
              rx="1.5"
            />
          )),
        )}
      </g>
      <rect y="166" width="320" height="14" fill="#312e81" />
    </>
  ),
  puzzle: (id) => {
    const colors = ["#fde047", "#f472b6", "#60a5fa", "#34d399", "#fb923c", "#a78bfa"];
    return (
      <>
        <defs>
          <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#7c3aed" />
            <stop offset="1" stopColor="#db2777" />
          </linearGradient>
        </defs>
        <rect width="320" height="180" fill={`url(#${id}-bg)`} />
        <g transform="translate(52 22)">
          {Array.from({ length: 4 }).map((_, r) =>
            Array.from({ length: 6 }).map((__, c) => {
              const color = colors[(r * 7 + c * 3) % colors.length];
              return (
                <g key={`${r}-${c}`} transform={`translate(${c * 36} ${r * 36})`}>
                  <rect width="30" height="30" rx="9" fill="#ffffff" opacity="0.14" />
                  <circle cx="15" cy="15" r="10" fill={color} />
                  <circle cx="11.5" cy="11.5" r="3" fill="#ffffff" opacity="0.55" />
                </g>
              );
            }),
          )}
        </g>
      </>
    );
  },
  racing: (id) => (
    <>
      <defs>
        <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffb86b" />
          <stop offset="1" stopColor="#f2557a" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill={`url(#${id}-bg)`} />
      <path
        d="M-20 180 C 80 120, 120 120, 170 90 S 280 40, 340 46 L 340 82 C 280 78, 230 100, 190 128 S 90 180, 40 200 Z"
        fill="#2b2140"
      />
      <path
        d="M10 186 C 90 136, 130 132, 178 108 S 282 60, 340 64"
        fill="none"
        stroke="#fff3d6"
        strokeWidth="3"
        strokeDasharray="12 10"
      />
      <g transform="translate(150 96) rotate(-14)">
        <rect x="0" y="0" width="58" height="24" rx="10" fill="#22d3ee" />
        <rect x="16" y="-10" width="22" height="14" rx="6" fill="#0e7490" />
        <circle cx="12" cy="26" r="7" fill="#111827" />
        <circle cx="46" cy="26" r="7" fill="#111827" />
      </g>
      <circle cx="60" cy="44" r="18" fill="#fff1c7" opacity="0.9" />
    </>
  ),
  word: (id) => {
    const letters = ["P", "L", "A", "Y", "W", "O", "R", "D"];
    return (
      <>
        <defs>
          <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#38bdf8" />
            <stop offset="1" stopColor="#4f46e5" />
          </linearGradient>
        </defs>
        <rect width="320" height="180" fill={`url(#${id}-bg)`} />
        {letters.map((l, i) => (
          <g key={i} transform={`translate(${40 + (i % 4) * 62} ${36 + Math.floor(i / 4) * 62})`}>
            <rect width="52" height="52" rx="12" fill="#fefce8" />
            <text
              x="26"
              y="35"
              textAnchor="middle"
              fontSize="26"
              fontWeight="700"
              fontFamily="ui-sans-serif, system-ui, sans-serif"
              fill="#1e1b4b"
            >
              {l}
            </text>
          </g>
        ))}
      </>
    );
  },
  farm: (id) => (
    <>
      <defs>
        <linearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#a5e6ff" />
          <stop offset="1" stopColor="#e0f7d4" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill={`url(#${id}-sky)`} />
      <circle cx="64" cy="48" r="22" fill="#ffe27a" />
      <path d="M0 132 Q 80 96 170 126 T 320 112 V180 H0 Z" fill="#6cc551" />
      <path d="M0 152 Q 110 128 210 150 T 320 146 V180 H0 Z" fill="#3fa34d" />
      <g transform="translate(196 82)">
        <path d="M0 26 L 30 4 L 60 26 Z" fill="#b91c1c" />
        <rect x="6" y="26" width="48" height="36" fill="#dc2626" />
        <rect x="22" y="40" width="16" height="22" fill="#fde68a" />
      </g>
      <g fill="#f59e0b">
        <circle cx="96" cy="150" r="6" />
        <circle cx="118" cy="156" r="6" />
        <circle cx="140" cy="150" r="6" />
      </g>
    </>
  ),
};
