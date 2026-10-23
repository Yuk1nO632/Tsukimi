"use strict";

// 1. 演示数据归 JavaScript 管理；这些是虚构条目，没有视频来源。
const animeList = [
  { id: "forest", title: "月光邮便局", category: "奇幻 / 日常", episodes: 12, description: "把没来得及说的话，寄给月亮另一端的人。", scene: "forest", lettering: "Letters\nto the Moon", kicker: "A STORY IN THE FOREST" },
  { id: "coast", title: "海风经过的夏天", category: "青春 / 治愈", episodes: 12, description: "小镇、海风，还有一个不想结束的夏天。", scene: "coast", lettering: "Where the\nSea Whispers", kicker: "A SUMMER TO REMEMBER" },
  { id: "evening", title: "黄昏的慢行列车", category: "旅行 / 日常", episodes: 10, description: "下一站没有目的地，只有沿途遇见的故事。", scene: "evening", lettering: "One More\nStop", kicker: "TAKE THE SLOW WAY HOME" },
];

// 2. 本轮只保存在当前页面的内存中。刷新会重新创建这个空集合。
// 后续实验再逐步引入 React、FastAPI 和 SQLite。
const favoriteIds = new Set();
let currentFilter = "all";

const grid = document.querySelector("#anime-grid");
const cardTemplate = document.querySelector("#anime-card-template");
const emptyState = document.querySelector("#empty-state");
const feedback = document.querySelector("#feedback");
const filterButtons = document.querySelectorAll("[data-filter]");

// 3. 根据当前数据决定页面显示什么。
function render() {
  const visibleAnime = animeList.filter((anime) => currentFilter === "all" || favoriteIds.has(anime.id));
  const fragment = document.createDocumentFragment();

  for (const anime of visibleAnime) {
    const card = cardTemplate.content.cloneNode(true);
    const isFavorite = favoriteIds.has(anime.id);
    card.querySelector(".poster").classList.add(`scene-${anime.scene}`);
    card.querySelector(".poster-kicker").textContent = anime.kicker;
    card.querySelector(".poster-lettering").textContent = anime.lettering;
    card.querySelector(".poster-number").textContent = `0${animeList.indexOf(anime) + 1}`;
    card.querySelector(".card-meta").textContent = anime.category;
    card.querySelector("h3").textContent = anime.title;
    card.querySelector(".card-description").textContent = anime.description;
    card.querySelector(".episode-count").textContent = `全 ${anime.episodes} 集 · 演示条目`;

    const button = card.querySelector(".favorite-button");
    button.dataset.animeId = anime.id;
    button.setAttribute("aria-pressed", String(isFavorite));
    button.setAttribute("aria-label", `${isFavorite ? "取消收藏" : "收藏"}《${anime.title}》`);
    button.querySelector(".favorite-icon").textContent = isFavorite ? "♥" : "♡";
    button.querySelector(".favorite-label").textContent = isFavorite ? "已收藏" : "收藏";
    fragment.append(card);
  }

  grid.replaceChildren(fragment);
  grid.hidden = visibleAnime.length === 0;
  emptyState.hidden = visibleAnime.length !== 0;
  document.querySelector(".library-total").textContent = String(animeList.length).padStart(2, "0");
  document.querySelector("#header-count").textContent = favoriteIds.size;
  document.querySelector("#filter-count").textContent = favoriteIds.size;

  for (const button of filterButtons) {
    const isActive = button.dataset.filter === currentFilter;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  }
}

// 4. 点击收藏：改变数据，再更新界面。不向服务器保存任何收藏。
grid.addEventListener("click", (event) => {
  const button = event.target.closest(".favorite-button");
  if (!button) return;

  const anime = animeList.find((item) => item.id === button.dataset.animeId);
  if (!anime) return;
  const wasFavorite = favoriteIds.has(anime.id);
  if (wasFavorite) favoriteIds.delete(anime.id);
  else favoriteIds.add(anime.id);

  render();
  feedback.textContent = wasFavorite ? `已取消收藏《${anime.title}》。` : `已收藏《${anime.title}》。`;

  // 更新卡片后恢复键盘焦点；筛选后条目消失时，移动到剩余按钮。
  const focusTarget = grid.querySelector(`[data-anime-id="${anime.id}"]`) || grid.querySelector(".favorite-button") || document.querySelector("#show-all");
  focusTarget.focus({ preventScroll: true });
});

for (const button of filterButtons) {
  button.addEventListener("click", () => {
    currentFilter = button.dataset.filter;
    render();
    feedback.textContent = currentFilter === "all" ? "正在显示全部演示条目。" : `当前收藏了 ${favoriteIds.size} 个故事。`;
  });
}

document.querySelector("#show-all").addEventListener("click", () => {
  currentFilter = "all";
  render();
  document.querySelector('[data-filter="all"]').focus({ preventScroll: true });
  feedback.textContent = "遇见喜欢的故事，就为它留一个位置。";
});

render();
