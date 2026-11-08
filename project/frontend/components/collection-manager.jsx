"use client";
import Link from "next/link";
import { useState } from "react";
import ContinueWatching from "./continue-watching";
import { useAccount } from "./account-provider";
import AnimeCard from "./anime-card";
import {
  collectionLabels,
  CollectionStatusPicker,
  useCollection,
} from "./collection-provider";
import { LoadFailure, SkeletonGrid } from "./portal-state";

export default function CollectionManager() {
  const account = useAccount();
  const { collectionItems, status, loadError, reloadCollection } =
    useCollection();
  const [tab, setTab] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("updated");
  const items = collectionItems
    .filter(
      (item) =>
        (tab === "all" || item.status === tab) &&
        `${item.anime.title} ${item.anime.originalTitle}`
          .toLowerCase()
          .includes(query.trim().toLowerCase()),
    )
    .sort((a, b) =>
      sort === "score"
        ? b.anime.score - a.anime.score
        : sort === "title"
          ? a.anime.title.localeCompare(b.anime.title, "zh")
          : b.updated_at - a.updated_at,
    );
  return (
    <div className="content-shell portal-page">
      <div className="portal-heading">
        <div>
          <span className="portal-eyebrow">我的片单</span>
          <h1>我的追番</h1>
          <p>管理想看、正在看和已经看完的番剧。</p>
        </div>
        <Link className="outline-button" href="/browse">
          添加番剧 ＋
        </Link>
      </div>
      <div className="collection-summary">
        {account.user ? `${account.user.nickname}的片单` : "匿名片单 · 当前浏览器"}
        <span>{account.user ? "已关联账号 · 切回页面时更新" : <Link href="/account">登录以跨设备同步 →</Link>}</span>
      </div>
      <ContinueWatching manage />
      <div className="collection-toolbar">
        <div className="portal-tabs" role="group" aria-label="追番状态筛选">
          {[["all", "全部"], ...Object.entries(collectionLabels)].map(
            ([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={tab === value}
                onClick={() => setTab(value)}
              >
                {label}
                <span>
                  {status === "ready"
                    ? collectionItems.filter(
                        (item) => value === "all" || item.status === value,
                      ).length
                    : "—"}
                </span>
              </button>
            ),
          )}
        </div>
        <div className="collection-tools">
          <input
            aria-label="搜索我的追番"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索片单"
          />
          <select
            aria-label="片单排序"
            value={sort}
            onChange={(event) => setSort(event.target.value)}
          >
            <option value="updated">最近修改</option>
            <option value="score">评分优先</option>
            <option value="title">片名排序</option>
          </select>
        </div>
      </div>
      {status === "loading" ? (
        <SkeletonGrid />
      ) : status === "error" ? (
        <LoadFailure error={loadError} retry={() => void reloadCollection()} />
      ) : items.length ? (
        <div className="anime-grid portal-grid collection-grid">
          {items.map((item) => (
            <article className="collection-entry" key={item.anime.id}>
              <AnimeCard anime={item.anime} />
              <div className="collection-entry-state">
                <CollectionStatusPicker anime={item.anime} />
                <small>
                  {new Intl.DateTimeFormat("zh-CN", {
                    month: "2-digit",
                    day: "2-digit",
                    timeZone: "Asia/Shanghai",
                  }).format(new Date(item.updated_at * 1000))}{" "}
                  修改
                </small>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="portal-empty">
          <h3>
            {query
              ? "片单里没有匹配的番剧"
              : tab === "all"
                ? "还没有添加番剧"
                : `还没有标记为“${collectionLabels[tab]}”的番剧`}
          </h3>
          <p>在番剧详情中选择追番状态，记录会保留在你的片单中。</p>
          <Link className="solid-button" href="/browse">
            浏览番剧
          </Link>
        </div>
      )}
    </div>
  );
}
