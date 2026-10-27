import { redirect } from "next/navigation";
import HomeDashboard from "../components/home-dashboard";
export default async function HomePage({ searchParams }) {
  const params = await searchParams;
  if (params.view === "favorites") redirect("/collection");
  if (typeof params.q === "string" && params.q.trim())
    redirect(`/search?q=${encodeURIComponent(params.q.slice(0, 100))}`);
  return <HomeDashboard />;
}
