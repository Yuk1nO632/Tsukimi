import { test } from "node:test";
import assert from "node:assert/strict";
import { selectPopularPicks } from "../lib/discovery.js";

test("low-sample perfect scores do not outrank well-supported popular picks", () => {
  const rows = [
    { id: "tiny", score: 10, ratingCount: 4 },
    { id: "well-rated", score: 8.8, ratingCount: 20000 },
    { id: "below-threshold", score: 7.9, ratingCount: 80000 },
    { id: "missing-votes", score: 9.5 },
  ];
  assert.deepEqual(
    selectPopularPicks(rows).map((row) => row.id),
    ["well-rated"],
  );
});
test("rating threshold, score ordering, tie support and result bound are respected without mutating source order", () => {
  const rows = [
    { id: "b", score: 8.2, ratingCount: 2000 },
    { id: "edge", score: 8, ratingCount: 1000 },
    { id: "a", score: 8.2, ratingCount: 3000 },
    { id: "highest", score: 9, ratingCount: 4000 },
  ];
  assert.deepEqual(
    selectPopularPicks(rows, 3).map((row) => row.id),
    ["highest", "a", "b"],
  );
  assert.deepEqual(
    rows.map((row) => row.id),
    ["b", "edge", "a", "highest"],
  );
  assert.ok(selectPopularPicks(rows).some((row) => row.id === "edge"));
});
test("missing data and unqualified items stay empty instead of using unrelated stand-ins", () => {
  assert.deepEqual(selectPopularPicks(null), []);
  assert.deepEqual(
    selectPopularPicks([
      { score: 10, ratingCount: 999 },
      { score: 0, ratingCount: 99999 },
      { score: NaN, ratingCount: 99999 },
    ]),
    [],
  );
});
