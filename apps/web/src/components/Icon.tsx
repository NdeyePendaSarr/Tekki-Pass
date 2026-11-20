/** Small inline icons (no icon font, nothing to download on 3G). Decorative by default. */
const PATHS = {
  check: "M5 12.5l4.5 4.5L19 7.5",
  shield: "M12 3l7 3v5.5c0 4.5-3 7.8-7 9.5-4-1.7-7-5-7-9.5V6l7-3z M9 12l2.2 2.2L15.5 10",
  bolt: "M13 2L4.5 13.5H11L10 22l8.5-11.5H12L13 2z",
  lock: "M7 11V8a5 5 0 0110 0v3 M5.5 11h13v10h-13z",
  wallet: "M3.5 7.5h15a2 2 0 012 2v9a2 2 0 01-2 2h-13a2 2 0 01-2-2v-11z M3.5 7.5l12-4v4 M16 14h2.5",
  qr: "M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h2v2h-2z M18 14h2v2 M14 18h2v2 M18 18h2v2h-2",
  phone:
    "M8 2.5h8a1.5 1.5 0 011.5 1.5v16a1.5 1.5 0 01-1.5 1.5H8A1.5 1.5 0 016.5 20V4A1.5 1.5 0 018 2.5z M11 18.5h2",
  copy: "M8 8h11v12H8z M5 16V4h11",
  key: "M14.5 9.5a4 4 0 11-1.2-2.8 M13.3 6.7L21 14.4v3h-3v-2h-2v-2h-2.2",
  user: "M12 12a4 4 0 100-8 4 4 0 000 8z M4.5 20.5c1-3.6 4-5.5 7.5-5.5s6.5 1.9 7.5 5.5",
  signal: "M4 19h2v-3H4z M9 19h2v-6H9z M14 19h2V9h-2z M19 19h2V5h-2z",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({
  name,
  size = 22,
  label,
}: {
  name: IconName;
  size?: number;
  label?: string;
}) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

/** The Tekki-Pass mark: a stacked brick wall with a check, for construction work proven. */
export function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#ffffff" />
      <g fill="#0f5132">
        <rect x="5" y="17" width="10" height="5" rx="1" />
        <rect x="17" y="17" width="10" height="5" rx="1" />
        <rect x="5" y="23.5" width="22" height="4" rx="1" />
      </g>
      <path
        d="M9 10.5l4 4 9-9"
        fill="none"
        stroke="#d98e2b"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
