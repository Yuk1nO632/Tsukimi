import Link from "next/link";

export default function NotFound() {
  return (
    <section className="not-found-page" aria-labelledby="not-found-title">
      <span className="eyebrow">A SMALL DETOUR</span>
      <span className="not-found-moon" aria-hidden="true">☾</span>
      <h1 id="not-found-title">这个故事还没到站</h1>
      <p>没有找到这个页面，回到发现页看看其他故事吧。</p>
      <Link className="primary-link" href="/">返回发现</Link>
    </section>
  );
}
