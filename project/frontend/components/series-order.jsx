"use client";

import Image from "next/image";
import Link from "next/link";
import useApi from "../lib/use-api";
import { platformLabel, releaseLabel } from "../lib/catalog-display";
import styles from "./series-order.module.css";

function OrderItem({ item, orderedIndex }) {
  const current = item.relation === "当前";
  return (
    <li className={styles.item} data-current={current ? "true" : undefined}>
      <Link
        prefetch={false}
        className={styles.link}
        href={"/anime/" + item.id}
        aria-current={current ? "page" : undefined}
      >
        <Image
          className={styles.cover}
          src={item.cover || "/covers/placeholder.svg"}
          alt=""
          width={48}
          height={64}
        />
        <span className={styles.copy}>
          <span className={styles.relation}>
            {orderedIndex !== undefined && <span>{orderedIndex + 1} · </span>}
            {current ? "当前作品" : item.relation}
          </span>
          <strong>{item.title}</strong>
          <small>{platformLabel(item.platform)} · {releaseLabel(item)}</small>
        </span>
      </Link>
    </li>
  );
}

export default function SeriesOrder({ animeId }) {
  const { data, error, retry } = useApi("/api/catalog/" + animeId + "/series");
  if (!error && !(data?.main?.length > 1 || data?.extras?.length || data?.partial)) return null;
  const ordered = data?.ordered && !data.partial && data.main.length > 1;
  const MainList = ordered ? "ol" : "ul";
  return (
    <section className={"series-section " + styles.section} aria-labelledby="series-order-title">
      <h2 id="series-order-title">系列观看顺序</h2>
      {error ? (
        <p className={styles.note} role="status">
          系列资料暂时无法读取。{" "}
          <button className="text-button" type="button" onClick={retry}>重试</button>
        </p>
      ) : (
        <>
          <p className={styles.note}>
            {ordered
              ? "根据 Bangumi 的前传与续集关系排列。"
              : data.partial || !data.ordered
                ? "观看顺序待确认，以下列出已取得的关联作品。"
                : "根据 Bangumi 的作品关联整理。"}
          </p>
          <MainList className={styles.list} aria-label="系列作品">
            {data.main.map((item, index) => (
              <OrderItem key={item.id} item={item} orderedIndex={ordered ? index : undefined} />
            ))}
          </MainList>
          {data.extras.length > 0 && (
            <div className={styles.extras}>
              <h3>番外与其他关联</h3>
              <ul className={styles.list} aria-label="番外与其他关联">
                {data.extras.map((item) => <OrderItem key={item.id} item={item} />)}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
