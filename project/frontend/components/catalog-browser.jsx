"use client";
import { useRouter } from "next/navigation";
import useApi from "../lib/use-api";
import { currentSeason, genres } from "../lib/catalog-params";
import AnimeCard from "./anime-card";
import { LoadFailure, SkeletonGrid } from "./portal-state";

export default function CatalogBrowser({ params, searching = false }) {
  const router = useRouter();
  const query = new URLSearchParams(
    Object.entries(params).filter(([, value]) => value),
  );
  const { data, error, loading, retry } = useApi(`/api/catalog?${query}`);
  const current = currentSeason();
  function apply(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = new URLSearchParams();
    for (const [key, value] of form)
      if (String(value).trim()) next.set(key, String(value).trim());
    router.push(`${searching ? "/search" : "/browse"}?${next}`);
  }
  function page(number) {
    const next = new URLSearchParams(query);
    next.set("page", String(number));
    router.push(`${searching ? "/search" : "/browse"}?${next}`);
  }
  return (
    <div className="content-shell portal-page">
      <div className="portal-heading">
        <div>
          <span className="portal-eyebrow">
            {searching ? "搜索" : "番剧索引"}
          </span>
          <h1>
            {searching && params.q ? `“${params.q}”的搜索结果` : "番剧资料库"}
          </h1>
          <p>搜索番名、原名或别名，筛选想看的动画。</p>
        </div>
      </div>
      <form
        className="catalog-filter-panel"
        role="search"
        aria-label="筛选番剧资料"
        onSubmit={apply}
      >
        <div className="catalog-query">
          <input
            name="q"
            aria-label="番剧资料关键词"
            defaultValue={params.q}
            maxLength={100}
            placeholder="输入番名、原名或别名"
          />
          <button className="solid-button" type="submit">
            搜索
          </button>
        </div>
        <div className="catalog-selects">
          <label>
            年份
            <select
              name="year"
              aria-label="筛选年份"
              defaultValue={params.year}
              onChange={(event) => event.currentTarget.form.requestSubmit()}
            >
              <option value="">全部年份</option>
              {Array.from(
                { length: current.year - 1988 },
                (_, i) => current.year + 1 - i,
              ).map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
              {params.year && Number(params.year) < 1990 && (
                <option value={params.year}>{params.year}</option>
              )}
            </select>
          </label>
          <label>
            季度
            <select
              name="season"
              aria-label="筛选季度"
              defaultValue={params.season}
              onChange={(event) => event.currentTarget.form.requestSubmit()}
            >
              <option value="">全部季度</option>
              {["冬季 · 1月", "春季 · 4月", "夏季 · 7月", "秋季 · 10月"].map(
                (label, i) => (
                  <option key={label} value={i + 1}>
                    {label}
                  </option>
                ),
              )}
            </select>
          </label>
          <label>
            类型
            <select
              name="genre"
              aria-label="筛选类型"
              defaultValue={params.genre}
              onChange={(event) => event.currentTarget.form.requestSubmit()}
            >
              <option value="">全部类型</option>
              {params.genre && !genres.includes(params.genre) && (
                <option value={params.genre}>{params.genre}</option>
              )}
              {genres.map((genre) => (
                <option key={genre}>{genre}</option>
              ))}
            </select>
          </label>
          <label>
            排序
            <select
              name="sort"
              aria-label="番剧排序"
              defaultValue={params.sort}
              onChange={(event) => event.currentTarget.form.requestSubmit()}
            >
              <option value="match">综合匹配</option>
              <option value="heat">收藏热度</option>
              <option value="score">评分优先</option>
              <option value="rank">排名优先</option>
            </select>
          </label>
          <button
            className="filter-reset"
            type="button"
            onClick={() => router.push(searching ? "/search" : "/browse")}
          >
            重置筛选
          </button>
        </div>
        {params.season && !params.year && (
          <p className="filter-note">
            未选年份，季度筛选按 {current.year} 年查询。
          </p>
        )}
      </form>
      <div className="catalog-result-heading">
        <span role="status">
          {loading
            ? "正在查询番剧资料…"
            : error
              ? "查询暂时不可用"
              : `共 ${data.total.toLocaleString()} 部 · 第 ${params.page} 页`}
        </span>
        <span>Bangumi 资料 · 收藏热度为资料站收藏人数</span>
      </div>
      {loading ? (
        <SkeletonGrid count={12} />
      ) : error ? (
        <LoadFailure error={error} retry={retry} />
      ) : data.items.length ? (
        <>
          <div className="anime-grid portal-grid">
            {data.items.map((anime) => (
              <AnimeCard key={anime.id} anime={anime} />
            ))}
          </div>
          <nav className="pagination" aria-label="结果分页">
            <button
              disabled={Number(params.page) <= 1}
              onClick={() => page(Number(params.page) - 1)}
            >
              上一页
            </button>
            <span>
              {params.page} /{" "}
              {Math.max(1, Math.min(200, Math.ceil(data.total / data.limit)))}
            </span>
            <button
              disabled={
                Number(params.page) * data.limit >= data.total ||
                Number(params.page) >= 200
              }
              onClick={() => page(Number(params.page) + 1)}
            >
              下一页
            </button>
          </nav>
        </>
      ) : (
        <div className="portal-empty">
          <h3>没有找到符合条件的番剧</h3>
          <p>试试原名或别名，或放宽年份和类型筛选。</p>
          <button
            className="outline-button"
            onClick={() => router.push("/browse")}
          >
            浏览全部番剧
          </button>
        </div>
      )}
    </div>
  );
}
