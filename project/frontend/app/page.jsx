import HomeLibrary from "../components/home-library";

// page.jsx 对应首页 /。searchParams 用来支持导航中的“我的追番”。
export default async function HomePage({ searchParams }) {
  const params = await searchParams;
  const initialView = params.view === "favorites" ? "favorites" : "all";
  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy">
          <span className="eyebrow">A LITTLE TIME FOR YOUR STORIES</span>
          <h1 id="hero-title">月下片刻，<br />故事未完<span className="accent-dot">。</span></h1>
          <p>把喜欢的故事留在这里。<br />从一份小小的追番单，开始下一集的期待。</p>
          <span className="hero-label"><span className="status-dot" aria-hidden="true" />Tsukimi · 我的追番时光</span>
        </div>
        <div className="moon-scene" aria-hidden="true">
          <span className="moon-orbit orbit-one" /><span className="moon-orbit orbit-two" /><span className="large-moon" />
          <span className="small-star star-one">✦</span><span className="small-star star-two">✧</span><span className="scene-caption">月がきれいですね</span>
        </div>
      </section>
      <HomeLibrary key={initialView} initialView={initialView} />
    </>
  );
}
