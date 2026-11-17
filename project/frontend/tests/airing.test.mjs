import { test } from "node:test";
import assert from "node:assert/strict";
import { airingSummary, episodeSchedule } from "../lib/airing.js";

test("airing labels distinguish the planned total from confirmed progress", () => {
  const anime = {
    episodes: 12,
    airing: { status: "airing", airedCount: 7, latestEpisode: 7 },
  };
  assert.equal(airingSummary(anime), "连载中 · 更新至第 7 集 · 共 12 集");
  assert.equal(
    airingSummary({ ...anime, airing: { status: "completed" } }),
    "已完结 · 共 12 集",
  );
  assert.equal(
    airingSummary({ ...anime, airing: { status: "upcoming" } }),
    "未开播 · 共 12 集",
  );
  assert.equal(airingSummary({ episodes: 0 }), "更新进度待确认 · 总集数待定");
  assert.match(
    airingSummary({
      episodes: 3,
      airing: { status: "unknown", airedCount: 2, latestEpisode: 3 },
    }),
    /已播 2 集 · 最新第 3 集/,
  );
});

test("future episodes are disabled individually and unknown dates stay unconfirmed", () => {
  const anime = {
    episodes: 4,
    airing: {
      episodes: [
        { number: 1, status: "aired", airdate: "2026-11-01" },
        { number: 3, status: "aired", airdate: "2026-11-03" },
        { number: 4, status: "upcoming", airdate: "2026-12-01" },
      ],
    },
  };
  assert.deepEqual(
    episodeSchedule(anime).map((row) => row.status),
    ["aired", "unknown", "aired", "upcoming"],
  );
  assert.equal(episodeSchedule(anime)[3].airdate, "2026-12-01");
  assert.equal(episodeSchedule(anime, 6).length, 4);
  assert.equal(
    episodeSchedule({ episodes: 0, airing: anime.airing }).length,
    4,
  );
});

test("older cached metadata retains episode entry points with unknown progress", () => {
  assert.equal(episodeSchedule({ episodes: 12 }).length, 12);
  assert.ok(
    episodeSchedule({ episodes: 12 }).every((row) => row.status === "unknown"),
  );
  assert.equal(episodeSchedule({ episodes: 0 }).length, 1);
  assert.ok(
    episodeSchedule({ episodes: 2, airing: { status: "upcoming" } }).every(
      (row) => row.status === "upcoming",
    ),
  );
  assert.equal(episodeSchedule({ episodes: 10001 }).length, 10000);
});
