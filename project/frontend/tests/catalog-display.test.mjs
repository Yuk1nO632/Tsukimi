import assert from "node:assert/strict";
import test from "node:test";
import { platformLabel, releaseLabel, searchPartLabel } from "../lib/catalog-display.js";

test("search metadata uses known seasons and handles partial dates", () => {
  assert.equal(releaseLabel({ releaseDate: "2026-10-02" }), "2026 年秋季");
  assert.equal(releaseLabel({ releaseDate: "2011-04" }), "2011 年春季");
  assert.equal(releaseLabel({ releaseDate: "2026-13-01", year: "2026" }), "2026 年");
  assert.equal(releaseLabel({}), "首播时间待定");
  assert.equal(platformLabel("Movie"), "剧场版");
});

test("search uses explicit season and arc labels without treating dates or title numbers as parts", () => {
  assert.equal(searchPartLabel({ title: "作品 第二季" }), "第二季");
  assert.equal(searchPartLabel({ originalTitle: "Same Name 第２期" }), "第2期");
  assert.equal(searchPartLabel({ title: "作品：无限列车篇" }), "无限列车篇");
  assert.equal(searchPartLabel({ title: "赛博朋克2077", releaseDate: "2026-01-01" }), "");
});
