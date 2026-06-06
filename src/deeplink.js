/**
 * deeplink.js — 横断ジャンプ解決エンジン（唯一の真実）
 *
 * (library_source, book_link, print_page) -> { status, url, viewer_page, ... }
 *
 * 「書名・章節・ページ」に着地させるための中核。サーバ(server.js)とブラウザ(viewer.js)の
 * 両方から同じロジックを使い、挙動のズレを防ぐ。Node の require でもブラウザの <script> でも動く。
 *
 * offset の定義: viewer_page = print_page + offset
 *   - office_pdf : viewer_page は PDF.js のページ番号（ファイル先頭からの位置）
 *   - 有償DL     : viewer_page は各ビューワーのページカウンタ
 *   - offset は本×ライブラリごとに「1点合わせ」で求める（calibrate）
 *
 * 返り値 status:
 *   "page"        ページ単位で着地できる（url, viewer_page あり）
 *   "book_top"    本のトップにのみ着地（offset未校正 or print_page不明）
 *   "physical"    物理本（URLなし。location と print_page を提示）
 *   "unavailable" その本はこのライブラリに無い（link なし）
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.Deeplink = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function fillTemplate(template, vars) {
    if (template == null) return null;
    return template.replace(/\{(\w+)\}/g, function (m, key) {
      return key in vars && vars[key] != null ? String(vars[key]) : m;
    });
  }

  function hasUnfilledPlaceholder(url) {
    return url != null && /\{\w+\}/.test(url);
  }

  /**
   * @param {object} source  config/library_sources.json の1要素
   * @param {object|null} link  book_links[bookId][source.id]（無ければ null）
   * @param {number|null} printPage  TOCノードの印刷ページ（p / page_start）。本トップなら null
   * @returns {object} 着地情報
   */
  function resolveLink(source, link, printPage) {
    if (!source) return { status: 'unavailable', source_id: null };
    const base = { source_id: source.id, label: source.label, short_label: source.short_label, tier: source.tier };

    // 物理本: URLは無い。棚位置と印刷ページを返す。
    if (source.page_strategy === 'locate' || source.kind === 'physical') {
      if (!link) return Object.assign(base, { status: 'unavailable' });
      return Object.assign(base, {
        status: 'physical',
        location: link.location || null,
        print_page: printPage != null ? printPage : null,
      });
    }

    // その本がこのライブラリに登録されていない
    if (!link) return Object.assign(base, { status: 'unavailable' });

    const offset = typeof link.offset === 'number' ? link.offset : null;
    const canPage = offset !== null && printPage != null && Number.isFinite(printPage);

    if (canPage) {
      const viewerPage = printPage + offset;
      const url = fillTemplate(source.url_template, Object.assign({}, link, { viewer_page: viewerPage, print_page: printPage }));
      // テンプレートに未解決の {placeholder} が残る（book_key欠落等）→ ページ着地不可
      if (url && !hasUnfilledPlaceholder(url)) {
        return Object.assign(base, { status: 'page', url, viewer_page: viewerPage, print_page: printPage, needs_auth: !!source.needs_auth });
      }
    }

    // フォールバック: 本トップに着地（offset未校正 / print_page不明 / page用テンプレート不完全）
    const topTemplate = source.book_url_template || source.url_template;
    const topUrl = fillTemplate(topTemplate, Object.assign({}, link, { viewer_page: '', print_page: printPage }));
    if (topUrl && !hasUnfilledPlaceholder(topUrl.replace('#page=', '#page=').replace(/\{viewer_page\}/, ''))) {
      // viewer_page だけ埋まっていなくてもトップとしては有効なケースを許容
      const cleaned = topUrl.replace(/[?&#]page=\s*$/, '').replace(/#page=$/, '');
      if (!hasUnfilledPlaceholder(cleaned)) {
        return Object.assign(base, {
          status: 'book_top',
          url: cleaned,
          print_page: printPage != null ? printPage : null,
          reason: canPage ? 'template_incomplete' : (offset === null ? 'offset_not_calibrated' : 'print_page_unknown'),
          needs_auth: !!source.needs_auth,
        });
      }
    }

    return Object.assign(base, { status: 'unavailable', reason: 'no_resolvable_url' });
  }

  /**
   * 1つのノード（または本）について、全ライブラリの着地候補をまとめて返す。
   * @param {Array} sources  library_sources.sources
   * @param {object} bookLinks  book_links[bookId]（{ source_id: link } のマップ）。無ければ {}
   * @param {number|null} printPage
   * @returns {Array} 各ライブラリの resolveLink 結果（unavailable も含む）
   */
  function resolveAll(sources, bookLinks, printPage) {
    bookLinks = bookLinks || {};
    return sources.map(function (src) {
      return resolveLink(src, bookLinks[src.id] || null, printPage);
    });
  }

  /**
   * 1点合わせ: 実ビューワーで「印刷ページ knownPrintPage を表示しているときの viewer ページ番号」から
   * offset を求める。 offset = knownViewerPage - knownPrintPage
   */
  function computeOffset(knownPrintPage, knownViewerPage) {
    if (!Number.isFinite(knownPrintPage) || !Number.isFinite(knownViewerPage)) return null;
    return knownViewerPage - knownPrintPage;
  }

  return { resolveLink: resolveLink, resolveAll: resolveAll, computeOffset: computeOffset, fillTemplate: fillTemplate };
});
