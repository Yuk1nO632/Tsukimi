import Link from "next/link";

export default function Brand({ footer = false }) {
  return (
    <Link
      className={`brand identity-brand${footer ? " footer-brand identity-brand-footer" : ""}`}
      href="/"
      aria-label="Tsukimi 首页"
    >
      <svg
        className="identity-mark"
        viewBox="0 0 36 36"
        width="32"
        height="32"
        fill="none"
        aria-hidden="true"
        focusable="false"
      >
        <path
          d="M11.99 5.35A14 14 0 1 0 29.01 26.65A14 14 0 0 1 11.99 5.35Z"
          fill="currentColor"
        />
      </svg>
      <span className="identity-wordmark">Tsukimi</span>
    </Link>
  );
}
