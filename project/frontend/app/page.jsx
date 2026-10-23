import FeaturedHero from "../components/featured-hero";
import HomeLibrary from "../components/home-library";
export default async function HomePage({ searchParams }) {
  const params = await searchParams;
  const initialView = params.view === "favorites" ? "favorites" : "all";
  const initialQuery = typeof params.q === "string" ? params.q.slice(0, 200) : "";
  return <><FeaturedHero /><HomeLibrary key={`${initialView}:${initialQuery}`} initialView={initialView} initialQuery={initialQuery} /></>;
}
