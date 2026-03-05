const DATA = {
  naver: "./data/naver_news.json",
  google: "./data/google_web.json",
  youtube: "./data/youtube.json",
  instagram: "./data/instagram.json",
};

let current = "naver";
let cache = {};

const $ = (sel) => document.querySelector(sel);
const listEl = $("#list");
const statusEl = $("#status");
const only7El = $("#only7");
const dedupeEl = $("#dedupeTitle");

function parseDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  return d;
}

function withinDays(iso, days) {
  const d = parseDate(iso);
  if (!d) return true; // 날짜 없으면 통과(웹문서/인스타 등)
  const now = new Date();
  const cutoff = new Date(now.getTime() - days * 24 * 3600 * 1000);
  return d >= cutoff;
}

function dedupeByTitle(items) {
  const seen = new Set();
  const out = [];
  for (const it of items) {
    const t = (it.title || "").trim().toLowerCase();
    if (!t) continue;
    if (seen.has(t)) continue;
    seen.add(t);
    out.push(it);
  }
  return out;
}

function sortLatest(items) {
  return [...items].sort((a,b) => {
    const da = parseDate(a.published_iso) ? parseDate(a.published_iso).getTime() : 0;
    const db = parseDate(b.published_iso) ? parseDate(b.published_iso).getTime() : 0;
    return db - da;
  });
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}

function render(items) {
  listEl.innerHTML = "";
  if (!items.length) {
    listEl.innerHTML = `<li class="item">결과가 없습니다. (인스타는 Graph API 설정이 필요할 수 있어요)</li>`;
    return;
  }
  for (const it of items) {
    const title = it.title || "(제목 없음)";
    const link = it.link || "#";
    const source = it.source || "";
    const time = it.published_kst || it.published_iso || "";
    const snip = it.snippet || "";

    const li = document.createElement("li");
    li.className = "item";
    li.innerHTML = `
      <div><a href="${link}" target="_blank" rel="noreferrer">${escapeHtml(title)}</a></div>
      <div class="meta">
        <span>${escapeHtml(source)}</span>
        <span>${escapeHtml(time)}</span>
        <span>${escapeHtml(it.platform || "")}</span>
      </div>
      ${snip ? `<div class="snip">${escapeHtml(snip)}</div>` : ""}
    `;
    listEl.appendChild(li);
  }
}

async function load(platform) {
  current = platform;
  statusEl.textContent = "불러오는 중…";

  if (!cache[platform]) {
    const res = await fetch(DATA[platform], { cache: "no-store" });
    cache[platform] = await res.json();
  }

  let items = cache[platform] || [];

  if (dedupeEl.checked) items = dedupeByTitle(items);
  if (only7El.checked) items = items.filter(it => withinDays(it.published_iso, 7));

  items = sortLatest(items);
  statusEl.textContent = `${items.length}개 표시 중`;
  render(items);
}

function setActiveTab(platform) {
  document.querySelectorAll(".tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.platform === platform);
  });
}

document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", async () => {
    const p = btn.dataset.platform;
    setActiveTab(p);
    await load(p);
  });
});

$("#refreshBtn").addEventListener("click", async () => {
  cache = {};
  await load(current);
});

only7El.addEventListener("change", () => load(current));
dedupeEl.addEventListener("change", () => load(current));

load("naver");
