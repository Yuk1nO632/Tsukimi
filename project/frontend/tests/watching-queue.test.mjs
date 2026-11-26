import assert from "node:assert/strict";
import test from "node:test";
import { buildWatchingQueue, dateInShanghai } from "../lib/watching-queue.js";

const tracked = (id, title = id) => ({ anime: { id, title }, updated_at: Date.parse("2026-11-24") / 1000 });
const episode = (number, airdate, status) => ({ number, airdate, status });

test("new releases offer the next confirmed episode without labeling unknown data or classic backlogs", () => {
  const items = [tracked("airing"), tracked("unknown"), tracked("classic"), tracked("rewatch")];
  const schedules = new Map([
    ["airing", { episodes: [episode(8, "2026-11-25", "aired"), episode(7, "2026-11-20", "aired")] }],
    ["unknown", { episodes: [episode(2, "", "unknown")] }],
    ["classic", { episodes: [episode(2, "2000-01-01", "aired")] }],
    ["rewatch", { episodes: [episode(7, "2026-11-25", "aired")] }],
  ]);
  const history = new Map([
    ["airing", { episode: 6 }],
    ["rewatch", { episode: 3, furthest_episode: 7 }],
  ]);
  const queue = buildWatchingQueue(items, schedules, history, "2026-11-26");
  assert.deepEqual(queue.releases.map(({anime, episode}) => [anime.id, episode.number]), [["airing", 7]]);
  assert.deepEqual(buildWatchingQueue(items, schedules, null, "2026-11-26").releases, []);
});

test("Shanghai dates and week boundaries keep the mobile timeline in chronological groups", () => {
  assert.equal(dateInShanghai(Date.parse("2026-11-25T16:10:00Z")), "2026-11-26");
  const dates = ["2026-11-26", "2026-11-27", "2026-11-29", "2026-11-30"];
  const items = dates.map((_, index) => tracked(String(index)));
  const schedules = new Map(dates.map((date, index) => [String(index), {
    episodes: [episode(1, date, "upcoming")],
  }]));
  const queue = buildWatchingQueue(items, schedules, new Map(), "2026-11-26");
  assert.deepEqual(queue.upcoming.map(([group, rows]) => [group, rows[0].anime.id]), [
    ["今天", "0"], ["明天", "1"], ["本周", "2"], ["稍后", "3"],
  ]);
});
