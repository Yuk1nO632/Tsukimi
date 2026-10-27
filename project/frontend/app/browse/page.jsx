import CatalogBrowser from "../../components/catalog-browser";
import { readCatalogParams } from "../../lib/catalog-params";
export const metadata = { title: "番剧索引" };
export default async function BrowsePage({ searchParams }) {
  const params = readCatalogParams(await searchParams);
  return <CatalogBrowser key={JSON.stringify(params)} params={params} />;
}
