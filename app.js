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

/* ---------- NEWS (NAVER/GOOGLE) ---------- */
let newsNaver = [];
let newsGoogle = [];
let currentSource = "naver";

function renderNews(items) {
  const ul = document.getElementById("news-list");
  ul.innerHTML = "";
  items.slice(0, 20).forEach(n => {
    const a = el("a", { href:n.link, target:"_blank", rel:"noreferrer" }, n.title);
    const meta = el("div", { class:"muted" },
      `${n.source || ""}${n.published_kst ? " · " + n.published_kst : ""}`
    );
    ul.appendChild(el("li", {}, a, meta));
  });
}

function parseDateSafe(iso) {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

function sortByNewest(items) {
  return [...items].sort((a,b) => {
    const da = parseDateSafe(a.published_iso);
    const db = parseDateSafe(b.published_iso);
    const ta = da ? da.getTime() : 0;
    const tb = db ? db.getTime() : 0;
    return tb - ta;
  });
}

function filterLast7Days(items) {
  const now = new Date();
  const cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  return items.filter(it => {
    const d = parseDateSafe(it.published_iso);
    if (!d) return false;
    return d >= cutoff;
  });
}

/** 제목 정규화: 괄호/따옴표/특수문자/여분 공백 제거해서 "유사 제목"도 중복으로 잡기 */
function normalizeTitle(t) {
  return (t || "")
    .toLowerCase()
    .replace(/\[[^\]]*\]/g, " ")   // [단독] 같은 태그 제거
    .replace(/\([^\)]*\)/g, " ")   // (종합) 같은 태그 제거
    .replace(/[“”"']/g, " ")
    .replace(/[\.\,\!\?\:\;\-\—\|\·]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** 동일 제목(정규화 기준) 중복 제거: 최신 것만 남기기 위해 정렬 후 앞에서부터 유지 */
function dedupeByTitle(items) {
  const seen = new Set();
  const out = [];
  for (const it of items) {
    const key = normalizeTitle(it.title);
    if (!key) continue;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(it);
  }
  return out;
}

function getActiveNewsList() {
  const srcList = (currentSource === "naver") ? newsNaver : newsGoogle;
  const weekOnly = document.getElementById("chk-week")?.checked;

  // 1) 최신순 정렬
  let out = sortByNewest(srcList);

  // 2) 7일 필터
  if (weekOnly) out = filterLast7Days(out);

  // 3) 동일 제목 1개만(정규화)
  out = dedupeByTitle(out);

  return out.slice(0, 20);
}

function setNewsSource(src){
  currentSource = src;

  const btnN = document.getElementById("btn-naver");
  const btnG = document.getElementById("btn-google");

  const isN = src === "naver";
  btnN.classList.toggle("active", isN);
  btnG.classList.toggle("active", !isN);
  btnN.setAttribute("aria-pressed", String(isN));
  btnG.setAttribute("aria-pressed", String(!isN));

  renderNews(getActiveNewsList());
}

/* ---------- YOUTUBE ---------- */
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

  // 뉴스(네이버/구글 분리)
  newsNaver = await loadJson("./data/naver_news.json") || [];
  newsGoogle = await loadJson("./data/google_news.json") || [];

  // 버튼/체크박스 이벤트
  document.getElementById("btn-naver").onclick = () => setNewsSource("naver");
  document.getElementById("btn-google").onclick = () => setNewsSource("google");
  document.getElementById("chk-week").onchange = () => renderNews(getActiveNewsList());

  // 기본값: 네이버
  setNewsSource("naver");

  // 유튜브
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
