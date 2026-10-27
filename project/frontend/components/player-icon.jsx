export default function PlayerIcon({ name, size = 20 }) {
  const paths = {
    play: <path d="m9 5 11 7-11 7Z" fill="currentColor" stroke="none" />,
    pause: <><path d="M8 5v14M16 5v14" strokeWidth="4" /></>,
    volume: <><path d="M11 5 6 9H3v6h3l5 4Z" /><path d="M15 8a6 6 0 0 1 0 8M18 5a10 10 0 0 1 0 14" /></>,
    mute: <><path d="M11 5 6 9H3v6h3l5 4Z" /><path d="m16 9 6 6m0-6-6 6" /></>,
    fullscreen: <path d="M9 3H3v6m12-6h6v6M3 15v6h6m12-6v6h-6" />,
    restore: <path d="M3 9h6V3m6 0v6h6M9 21v-6H3m18 0h-6v6" />,
    wide: <rect x="2" y="5" width="20" height="14" rx="2" />,
    next: <><path d="m5 5 10 7-10 7Z" fill="currentColor" stroke="none" /><path d="M19 5v14" /></>,
    search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5" /><path d="M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.play}</svg>;
}
