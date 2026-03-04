async function loadJson(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) return null;
  return await res.json();
}

function setActiveTab(tab) {
  document.querySelectorAll(".tab").forEach(a => {
    a.classList.toggle("active", a.dataset.tab === tab);
  });
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  const view = document.getElementById(`view-${tab}`);
  if (view) view.classList.add("active");
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k,v]) => node.setAttribute(k, v));
  children.forEach(c => node.appendChild(typeof c === "string" ? document.createTextNode(c) : c));
  return node;
}

function renderNews(items) {
  const ul = document.getElementById("news-list");
  ul.innerHTML = "";
  items.slice(0, 20).forEach(n => {
    const a = el("a", { href:n.link, target:"_blank", rel:"noreferrer" }, n.title);
    const meta = el("div", { class:"muted" }, `${n.source || ""}${n.published ? " · " + n.published : ""}`);
    ul.appendChild(el("li", {}, a, meta));
  });
}

function renderYt(items, mountId, limit=10) {
  const wrap = document.getElementById(mountId);
  wrap.innerHTML = "";
  items.slice(0, limit).forEach(v => {
    const img = v.thumbnail
      ? el("img", { src:v.thumbnail, alt:v.title, loading:"lazy" })
      : el("div", { class:"thumb" }, "");
    const title = el("div", { class:"title" }, v.title);
    const meta = el("div", { class:"muted" }, v.published_kst || "");
    const card = el("a", { class:"yt-card", href:v.link, target:"_blank", rel:"noreferrer" }, img, title, meta);
    wrap.appendChild(card);
  });
}

async function refreshData() {
  const updated = await loadJson("./data/updated.json");
  document.getElementById("updated").textContent =
    updated?.updated_kst ? `마지막 갱신(KST): ${updated.updated_kst}` : "";

  const news = await loadJson("./data/news.json") || [];
  renderNews(news);

  const ytChannel = await loadJson("./data/youtube_channel.json") || [];
  renderYt(ytChannel, "yt-channel", 10);

  const ytSearch = await loadJson("./data/youtube_search.json");
  const note = document.getElementById("yt-search-note");
  if (!ytSearch || ytSearch.length === 0) {
    renderYt([], "yt-search", 10);
    note.textContent = "YouTube 검색 섹션은 API 키(YT_API_KEY)가 없으면 비어있을 수 있어요.";
  } else {
    renderYt(ytSearch, "yt-search", 10);
    note.textContent = "";
  }
}

function bootTabs() {
  const tab = (location.hash || "#news").replace("#", "");
  setActiveTab(tab);

  window.addEventListener("hashchange", () => {
    const t = (location.hash || "#news").replace("#", "");
    setActiveTab(t);
  });
}

(async function init(){
  bootTabs();
  await refreshData();
})();
