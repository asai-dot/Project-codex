/**
 * server.js — 事務所ライブラリ横断ビューワー（検索 / ジャンプ / 目次・本文コピー）
 *
 * Fork2（検索・RAG）の人間向け第一弾。4つのデータ保存（自炊PDF / ベンコム /
 * リーガルライブラリ / 物理本）を1つのビューワーから横断し、
 *   - 目次（章節）テキストを横断検索し「書名・章節・ページ」に着地
 *   - 各図書館へページ単位（offset校正済）またはトップへジャンプ
 *   - 目次を機械可読（Markdown/JSON）でコピー、引用ハンドルをコピー
 * を実現する。Node 標準モジュールのみ（npm不要）。既存 app/server.js の流儀を踏襲。
 *
 * 主なAPI:
 *   GET  /api/libraries            4図書館の設定
 *   GET  /api/search?q=...         目次横断検索（着地＋各図書館リンク付き）
 *   GET  /api/toc/:bookId          1冊の目次ツリー（クリーン済）
 *   GET  /api/book/:bookId         書誌＋目次＋全図書館リンク（詳細ビュー用）
 *   GET  /api/resolve?book=&source=&page=   単発のジャンプ解決
 *   POST /api/calibrate            1点合わせ（offset確定→book_links.json保存）
 *   GET  /pdf_orig/:folder/:file   自炊PDF配信（Range対応。PDF_BASE未設定/未配置なら404）
 */
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const Deeplink = require('../src/deeplink.js');
const Search = require('../src/search.js');

const PORT = parseInt(process.env.PORT || '3100', 10);
const REPO = path.resolve(__dirname, '..');
// データの所在は環境変数で上書き可（本番は Box 生成のインデックスを直接指せる）。
const DATA_DIR = process.env.DATA_DIR || path.join(REPO, 'data');
const CONFIG_DIR = process.env.CONFIG_DIR || path.join(REPO, 'config');
const PUBLIC_DIR = path.join(REPO, 'public');
const TOC_DIR = process.env.TOC_DIR || path.join(DATA_DIR, 'toc');
const INDEX_PATH = process.env.INDEX_PATH || path.join(DATA_DIR, 'toc_search_index.json');
const BOOK_LINKS_PATH = process.env.BOOK_LINKS_PATH || path.join(DATA_DIR, 'book_links.json');
// 自炊PDFの原本ベース（本番は Box『し＿自炊書籍データ』。未設定ならPDF配信は無効）
const PDF_BASE = process.env.PDF_BASE || '';

function readJson(p, fallback) {
  try { return JSON.parse(fs.readFileSync(p, 'utf-8')); } catch (e) { return fallback; }
}

// --- 起動時ロード ---
let SOURCES = (readJson(path.join(CONFIG_DIR, 'library_sources.json'), { sources: [] }).sources) || [];
let INDEX = readJson(INDEX_PATH, { books: {} });
let BOOK_LINKS = (readJson(BOOK_LINKS_PATH, { links: {} }).links) || {};
let BOOKS = (function () {
  const raw = readJson(path.join(DATA_DIR, 'books.json'), { books: [] });
  const list = raw.books || raw;
  const map = {};
  (Array.isArray(list) ? list : []).forEach(b => {
    const id = b.book_id || (b.isbn ? `isbn_${b.isbn}` : null);
    if (id) map[id] = b;
  });
  return map;
})();

function reloadBookLinks() {
  BOOK_LINKS = (readJson(BOOK_LINKS_PATH, { links: {} }).links) || {};
}

// 起動時に全ノードへ正規化キーを前計算（124k+ノードでも検索ごとの再正規化を避ける）。
function precomputeIndex(index) {
  let n = 0;
  for (const book of Object.values((index && index.books) || {})) {
    for (const node of book.nodes || []) {
      node._n = Search.normalize(node.t);          // タイトル正規化（空白保持）
      node._lk = Search.looseKey(node.t);          // タイトル空白無視
      node._np = Search.normalize(node.path);      // 章節パス正規化
      node._lpk = Search.looseKey(node.path);      // 章節パス空白無視
      n++;
    }
  }
  return n;
}
precomputeIndex(INDEX);

// --- 検索 ---
// 正規化済みクエリ(nq=空白保持 / lq=空白無視)でノードを採点。match は当たった箇所。
function scoreNode(node, nq, lq) {
  if (!node._n) return null;
  let s, match;
  if (node._n === nq) { s = 100; match = 'title'; }
  else if (node._n.startsWith(nq)) { s = 80; match = 'title'; }
  else if (node._n.includes(nq)) { s = 60; match = 'title'; }
  else if (lq && node._lk.includes(lq)) { s = 50; match = 'title_loose'; }
  else if (node._np.includes(nq)) { s = 40; match = 'path'; }
  else if (lq && node._lpk.includes(lq)) { s = 30; match = 'path_loose'; }
  else return null;
  if (node.p != null) s += 5;          // ページがある＝着地できる
  s += Math.max(0, 4 - (node.d || 1)); // 浅い見出しを微優先
  return { s, match };
}

function landingLabel(book, node) {
  const title = book.title || node.book_id;
  const page = node.p != null ? `p.${node.p}` : 'ページ不明';
  return `${title} ／ ${node.path || node.t} ／ ${page}`;
}

function search(q, limit) {
  const nq = Search.normalize((q || '').trim());
  const lq = Search.looseKey((q || '').trim());
  if (!nq) return [];
  const results = [];
  for (const [bookId, book] of Object.entries(INDEX.books || {})) {
    for (const node of book.nodes || []) {
      const hit = scoreNode(node, nq, lq);
      if (hit) {
        results.push({ book_id: bookId, title: book.title, isbn: book.isbn, score: hit.s, match: hit.match, node });
      }
    }
  }
  results.sort((a, b) => b.score - a.score || (a.node.p || 1e9) - (b.node.p || 1e9));
  return results.slice(0, limit || 30).map(r => ({
    book_id: r.book_id,
    title: r.title,
    isbn: r.isbn,
    score: r.score,
    match: r.match,
    node: { t: r.node.t, p: r.node.p, path: r.node.path, id: r.node.id, src: r.node.src, depth: r.node.d },
    landing: landingLabel({ title: r.title }, Object.assign({ book_id: r.book_id }, r.node)),
    links: Deeplink.resolveAll(SOURCES, BOOK_LINKS[r.book_id] || {}, r.node.p),
  }));
}

// --- HTTP helpers ---
function sendJson(res, data, code) {
  const body = JSON.stringify(data);
  res.writeHead(code || 200, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': Buffer.byteLength(body) });
  res.end(body);
}
function send404(res) { res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }); res.end('Not Found'); }

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };

function sendFile(res, filePath) {
  fs.stat(filePath, (err, st) => {
    if (err || !st.isFile()) return send404(res);
    res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream', 'Content-Length': st.size, 'Cache-Control': 'no-cache' });
    fs.createReadStream(filePath).pipe(res);
  });
}

function safeId(id) { return id && !id.includes('..') && !id.includes('/') && !id.includes('\\'); }

function bookDetail(bookId) {
  const book = BOOKS[bookId] || (INDEX.books[bookId] ? { book_id: bookId, title: INDEX.books[bookId].title, isbn: INDEX.books[bookId].isbn } : null);
  let nodes = [];
  const tocPath = path.join(TOC_DIR, `${bookId}.json`);
  try {
    const raw = JSON.parse(fs.readFileSync(tocPath, 'utf-8'));
    nodes = Array.isArray(raw) ? raw : [];
  } catch (e) { /* fall back to index */
    if (INDEX.books[bookId]) nodes = INDEX.books[bookId].nodes || [];
  }
  return {
    book_id: bookId,
    book: book,
    links: BOOK_LINKS[bookId] || {},
    library_status: SOURCES.map(s => {
      const link = (BOOK_LINKS[bookId] || {})[s.id] || null;
      return { source_id: s.id, label: s.label, short_label: s.short_label, tier: s.tier, available: !!link, has_offset: !!(link && typeof link.offset === 'number') };
    }),
    nodes: nodes,
  };
}

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url, true);
  const pathname = decodeURIComponent(parsed.pathname);

  if (pathname === '/api/health') return sendJson(res, { ok: true, books: Object.keys(INDEX.books || {}).length, sources: SOURCES.length });
  if (pathname === '/api/libraries') return sendJson(res, { sources: SOURCES });

  if (pathname === '/api/search') return sendJson(res, { q: parsed.query.q || '', results: search(parsed.query.q, parseInt(parsed.query.limit || '30', 10)) });

  if (pathname.startsWith('/api/toc/')) {
    const id = pathname.slice('/api/toc/'.length);
    if (!safeId(id)) return send404(res);
    const d = bookDetail(id);
    return sendJson(res, { book_id: id, title: d.book && d.book.title, nodes: d.nodes });
  }

  if (pathname.startsWith('/api/book/')) {
    const id = pathname.slice('/api/book/'.length);
    if (!safeId(id)) return send404(res);
    return sendJson(res, bookDetail(id));
  }

  if (pathname === '/api/resolve') {
    const bookId = parsed.query.book;
    const sourceId = parsed.query.source;
    const page = parsed.query.page != null && parsed.query.page !== '' ? parseInt(parsed.query.page, 10) : null;
    const src = SOURCES.find(s => s.id === sourceId);
    if (!src) return sendJson(res, { error: 'unknown source' }, 400);
    const link = (BOOK_LINKS[bookId] || {})[sourceId] || null;
    return sendJson(res, Deeplink.resolveLink(src, link, page));
  }

  // 1点合わせ: { book_id, source_id, print_page, viewer_page } -> offset を保存
  if (pathname === '/api/calibrate' && req.method === 'POST') {
    let body = '';
    req.on('data', c => { body += c; if (body.length > 1e5) req.destroy(); });
    req.on('end', () => {
      let payload;
      try { payload = JSON.parse(body); } catch (e) { return sendJson(res, { error: 'bad json' }, 400); }
      // 実ビューワーURLが貼られたら source_id / book_key / viewer_page を自動抽出
      if (payload.url) {
        const parsed = Deeplink.parseViewerUrl(SOURCES, payload.url);
        if (parsed) {
          if (!payload.source_id) payload.source_id = parsed.source_id;
          if (payload.book_key == null && parsed.book_key != null) payload.book_key = parsed.book_key;
          if (payload.viewer_page == null && parsed.viewer_page != null) payload.viewer_page = parsed.viewer_page;
        }
      }
      const { book_id, source_id, print_page, viewer_page, book_key, folder, file, location } = payload;
      if (!book_id || !source_id) return sendJson(res, { error: 'book_id and source_id required' }, 400);
      const offset = Deeplink.computeOffset(Number(print_page), Number(viewer_page));
      const file_path = BOOK_LINKS_PATH;
      const doc = readJson(file_path, { links: {} });
      doc.links = doc.links || {};
      const entry = Object.assign({}, doc.links[book_id] && doc.links[book_id][source_id]);
      if (offset != null) entry.offset = offset;
      if (book_key != null) entry.book_key = book_key;
      if (folder != null) entry.folder = folder;
      if (file != null) entry.file = file;
      if (location != null) entry.location = location;
      doc.links[book_id] = Object.assign({}, doc.links[book_id], { [source_id]: entry });
      try {
        fs.writeFileSync(file_path, JSON.stringify(doc, null, 2), 'utf-8');
        reloadBookLinks();
        return sendJson(res, { ok: true, book_id, source_id, saved: entry });
      } catch (e) { return sendJson(res, { error: String(e) }, 500); }
    });
    return;
  }

  // 自炊PDF配信（本番のみ。PDF_BASE 未設定や未配置は404）
  if (pathname.startsWith('/pdf_orig/')) {
    if (!PDF_BASE) { res.writeHead(404, { 'Content-Type': 'application/json' }); return res.end(JSON.stringify({ error: 'PDF_BASE not configured (本番では自炊PDFの原本ベースを環境変数 PDF_BASE で指定)' })); }
    const parts = pathname.slice('/pdf_orig/'.length).split('/');
    if (parts.length < 2 || parts.some(p => p.includes('..'))) return send404(res);
    const pdfPath = path.join(PDF_BASE, parts[0], parts.slice(1).join('/'));
    return fs.stat(pdfPath, (err, st) => {
      if (err) return send404(res);
      const range = req.headers.range;
      if (range) {
        const m = range.replace(/bytes=/, '').split('-');
        const start = parseInt(m[0], 10), end = m[1] ? parseInt(m[1], 10) : st.size - 1;
        res.writeHead(206, { 'Content-Range': `bytes ${start}-${end}/${st.size}`, 'Accept-Ranges': 'bytes', 'Content-Length': end - start + 1, 'Content-Type': 'application/pdf' });
        return fs.createReadStream(pdfPath, { start, end }).pipe(res);
      }
      res.writeHead(200, { 'Content-Type': 'application/pdf', 'Content-Length': st.size, 'Accept-Ranges': 'bytes' });
      fs.createReadStream(pdfPath).pipe(res);
    });
  }

  // 静的配信（ビューワー）。src/deeplink.js もブラウザから読めるよう公開。
  if (pathname === '/' || pathname === '/index.html') return sendFile(res, path.join(PUBLIC_DIR, 'viewer.html'));
  if (pathname === '/src/deeplink.js') return sendFile(res, path.join(REPO, 'src', 'deeplink.js'));
  const rel = pathname.replace(/^\//, '');
  const filePath = path.join(PUBLIC_DIR, rel);
  if (!filePath.startsWith(PUBLIC_DIR)) return send404(res);
  return sendFile(res, filePath);
});

if (require.main === module) {
  server.listen(PORT, process.env.BIND || '127.0.0.1', () => {
    console.log(`\n  事務所ライブラリ横断ビューワー  http://localhost:${PORT}`);
    console.log(`  蔵書 ${Object.keys(INDEX.books || {}).length} 冊 / 図書館 ${SOURCES.length} 系統`);
    console.log(`  PDF_BASE: ${PDF_BASE || '(未設定 — 自炊PDF配信は無効)'}\n`);
  });
}
module.exports = { server, search, bookDetail };
