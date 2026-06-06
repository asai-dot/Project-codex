/* viewer.js — 事務所ライブラリ横断ビューワー（フロント） */
'use strict';

let SOURCES = [];
let SOURCE_BY_ID = {};

const $ = (s, r) => (r || document).querySelector(s);
const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };

function toast(msg) {
  const t = $('#toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), 1600);
}
async function copy(text, label) {
  try { await navigator.clipboard.writeText(text); }
  catch (e) { const ta = el('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
  toast((label || 'コピー') + 'しました');
}

function tierClass(tier, kind) { return kind === 'physical' ? 'physical' : (tier === 'paid' ? 'paid' : 'owned'); }

/* 1ノード分の全図書館リンクを描画 */
function renderLinks(links) {
  const wrap = el('div', 'links');
  links.forEach(L => {
    const src = SOURCE_BY_ID[L.source_id] || {};
    const cls = tierClass(L.tier || src.tier, src.kind);
    if (L.status === 'page') {
      const a = el('a', `lib ${cls}`); a.href = L.url; a.target = '_blank'; a.rel = 'noopener';
      a.append(el('span', null, L.short_label || L.source_id), el('span', 'mode', `p.${L.viewer_page}`));
      wrap.appendChild(a);
    } else if (L.status === 'book_top') {
      const a = el('a', `lib ${cls} top`); a.href = L.url; a.target = '_blank'; a.rel = 'noopener';
      a.title = L.reason === 'offset_not_calibrated' ? 'offset未校正のためトップに着地（校正するとページ着地）' : 'トップに着地';
      a.append(el('span', null, L.short_label || L.source_id), el('span', 'mode', 'トップ'));
      wrap.appendChild(a);
    } else if (L.status === 'physical') {
      const s = el('span', `lib ${cls}`); s.title = 'クリックで棚位置をコピー';
      s.append(el('span', null, L.short_label || '物理本'), el('span', 'mode', `${L.location || '?'}${L.print_page != null ? ' p.' + L.print_page : ''}`));
      s.style.cursor = 'pointer';
      s.onclick = () => copy(`${L.location || ''} p.${L.print_page != null ? L.print_page : '?'}`, '棚位置を');
      wrap.appendChild(s);
    } else {
      const s = el('span', 'lib unavailable'); s.append(el('span', null, L.short_label || L.source_id), el('span', 'mode', '—')); wrap.appendChild(s);
    }
  });
  return wrap;
}

/* ---- 検索 ---- */
async function doSearch() {
  const q = $('#q').value.trim();
  const body = $('#results-body');
  if (!q) { body.innerHTML = '<p class="hint">検索語を入力してください。</p>'; return; }
  body.innerHTML = '<p class="hint">検索中…</p>';
  const res = await fetch('/api/search?q=' + encodeURIComponent(q)).then(r => r.json());
  body.innerHTML = '';
  if (!res.results.length) { body.innerHTML = `<p class="hint">「${q}」に一致する章節は見つかりませんでした。</p>`; return; }
  const head = el('p', 'hint', `「${res.q}」 ${res.results.length}件 — 上位ほど着地精度が高い順`);
  body.appendChild(head);
  res.results.forEach(r => {
    const card = el('div', 'result');
    const landing = el('div', 'landing', r.landing);
    landing.title = 'この本の目次・全図書館リンクを開く';
    landing.onclick = () => openBook(r.book_id);
    const crumb = el('div', 'crumb');
    crumb.append(document.createTextNode(`${r.node.path || r.node.t}`));
    const src = el('span', 'src', r.node.src); crumb.appendChild(src);
    card.append(landing, crumb, renderLinks(r.links));
    body.appendChild(card);
  });
}

/* ---- 書誌・目次詳細 ---- */
let CURRENT = null;
async function openBook(bookId) {
  const d = await fetch('/api/book/' + encodeURIComponent(bookId)).then(r => r.json());
  CURRENT = d;
  $('#detail-title').textContent = (d.book && d.book.title) || bookId;
  const actions = $('#detail-actions'); actions.innerHTML = '';
  const bMd = el('button', 'copybtn', '目次をコピー(Markdown)'); bMd.onclick = () => copy(tocMarkdown(d), '目次(Markdown)を');
  const bJson = el('button', 'copybtn', '目次をコピー(JSON)'); bJson.onclick = () => copy(tocJson(d), '目次(JSON)を');
  actions.append(bMd, bJson);

  const body = $('#detail-body'); body.innerHTML = '';
  // 図書館ステータス
  const status = el('div', 'statusbar');
  d.library_status.forEach(s => {
    const c = el('span', 'chip' + (s.available ? ' on' : '') + (s.available ? (s.has_offset ? ' page' : (SOURCE_BY_ID[s.source_id] && SOURCE_BY_ID[s.source_id].kind === 'physical' ? '' : ' top')) : ''), s.short_label);
    status.appendChild(c);
  });
  body.appendChild(status);

  // 目次ツリー
  const ul = el('ul', 'toc');
  (d.nodes || []).forEach((n, i) => {
    const t = (n.t || '').trim(); if (t.length < 2) return;
    const li = el('li');
    const row = el('div', `node d${Math.min(n.depth || n.l || 1, 4)}`);
    const title = el('span', 't', t); title.onclick = () => toggleJump(li, n, d);
    const page = (n.page_start != null ? n.page_start : n.p);
    row.append(title);
    if (page != null) row.appendChild(el('span', 'pg', `p.${page}`));
    const handle = el('button', 'copybtn', '引用'); handle.title = '引用ハンドル（書名・章節・ページ・各図書館リンク）をコピー';
    handle.style.cssText = 'margin-left:auto;font-size:11px;padding:2px 7px';
    handle.onclick = (e) => { e.stopPropagation(); copy(citationHandle(d, n), '引用ハンドルを'); };
    row.appendChild(handle);
    li.appendChild(row);
    ul.appendChild(li);
  });
  body.appendChild(ul);

  // 校正フォーム（有償DL・未校正のものだけ）
  d.library_status.filter(s => SOURCE_BY_ID[s.source_id] && SOURCE_BY_ID[s.source_id].page_strategy === 'offset_url' && (!s.has_offset))
    .forEach(s => body.appendChild(calibForm(d, s)));
}

function toggleJump(li, node, d) {
  const existing = li.querySelector('.jumpmenu');
  if (existing) { existing.remove(); return; }
  const page = (node.page_start != null ? node.page_start : node.p);
  const links = Deeplink.resolveAll(SOURCES, d.links || {}, page != null ? page : null);
  const menu = el('div', 'jumpmenu');
  menu.append(el('div', 'crumb', `${(d.book && d.book.title) || ''} ／ ${node.t} ／ ${page != null ? 'p.' + page : 'ページ不明'}`));
  menu.appendChild(renderLinks(links));
  li.appendChild(menu);
}

/* ---- コピー生成 ---- */
function tocMarkdown(d) {
  const lines = [`# ${(d.book && d.book.title) || d.book_id}${d.book && d.book.author ? ' / ' + d.book.author : ''}`];
  if (d.book && d.book.isbn) lines.push(`ISBN: ${d.book.isbn}`);
  lines.push('');
  (d.nodes || []).forEach(n => {
    const t = (n.t || '').trim(); if (t.length < 2) return;
    const depth = Math.min(n.depth || n.l || 1, 6);
    const page = (n.page_start != null ? n.page_start : n.p);
    lines.push(`${'  '.repeat(depth - 1)}- ${t}${page != null ? `  (p.${page})` : ''}`);
  });
  return lines.join('\n');
}
function tocJson(d) {
  return JSON.stringify({
    book_id: d.book_id,
    title: d.book && d.book.title,
    isbn: d.book && d.book.isbn,
    nodes: (d.nodes || []).filter(n => (n.t || '').trim().length >= 2).map(n => ({
      t: (n.t || '').trim(), depth: n.depth || n.l || 1,
      page: n.page_start != null ? n.page_start : (n.p != null ? n.p : null),
      toc_node_id: n.toc_node_id || n.id || null, path_id: n.toc_path_id || null,
    })),
  }, null, 2);
}
function citationHandle(d, node) {
  const page = (node.page_start != null ? node.page_start : node.p);
  const links = Deeplink.resolveAll(SOURCES, d.links || {}, page != null ? page : null);
  return JSON.stringify({
    book: d.book && d.book.title, isbn: d.book && d.book.isbn,
    chapter: node.t, page: page != null ? page : null,
    toc_node_id: node.toc_node_id || node.id || null,
    deeplinks: links.filter(L => L.status === 'page' || L.status === 'book_top').map(L => ({ source: L.source_id, mode: L.status, url: L.url })),
  }, null, 2);
}

/* ---- 校正（1点合わせ） ---- */
function calibForm(d, s) {
  const box = el('div', 'calib');
  box.appendChild(el('h4', null, `${s.short_label} の offset を1点合わせ`));
  box.appendChild(el('div', 'hint', `実ビューワーで任意の本文ページを開き、その「印刷ページ」と「ビューワー側のページ番号」を入力すると offset を確定します（offset = ビューワー − 印刷）。`));
  const row = el('div', 'row');
  const bk = el('input'); bk.placeholder = 'book_key（任意）'; bk.style.width = '160px';
  const pp = el('input'); pp.type = 'number'; pp.placeholder = '印刷ページ'; pp.style.width = '100px';
  const vp = el('input'); vp.type = 'number'; vp.placeholder = 'ビューワーページ'; vp.style.width = '130px';
  const btn = el('button', 'copybtn', '保存');
  btn.onclick = async () => {
    const payload = { book_id: d.book_id, source_id: s.source_id, print_page: Number(pp.value), viewer_page: Number(vp.value) };
    if (bk.value.trim()) payload.book_key = bk.value.trim();
    const r = await fetch('/api/calibrate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).then(x => x.json());
    if (r.ok) { toast(`${s.short_label} offset=${r.saved.offset} を保存`); openBook(d.book_id); }
    else toast('保存失敗: ' + (r.error || ''));
  };
  row.append(bk, pp, vp, btn);
  box.appendChild(row);
  return box;
}

/* ---- 起動 ---- */
async function init() {
  const lib = await fetch('/api/libraries').then(r => r.json());
  SOURCES = lib.sources || [];
  SOURCE_BY_ID = Object.fromEntries(SOURCES.map(s => [s.id, s]));
  const legend = $('#legend');
  SOURCES.forEach(s => {
    const cls = tierClass(s.tier, s.kind);
    const item = el('span'); const dot = el('span', 'dot');
    dot.style.background = getComputedStyle(document.documentElement).getPropertyValue('--' + cls).trim() || '#999';
    item.append(dot, document.createTextNode(`${s.label}（${s.tier === 'paid' ? '有償' : '無料'}）`));
    legend.appendChild(item);
  });
  $('#go').onclick = doSearch;
  $('#q').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
}
init();
