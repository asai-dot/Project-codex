#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D1文献編 カタログ発掘スクリプト

【戦略】
  年別RTF取得ではなく、検索結果左サイドバーの「掲載誌」ファセットから
  誌名を一括取得する。年フィルタ（発行年月日フィールドが薄い）より確実。

  1. 空検索 or 幅広キーワード検索で大量の結果を出す
  2. 結果サイドバーの「掲載誌」絞り込みリストを展開して全誌名を回収
  3. 複数キーワードで繰り返してカバレッジを広げる
  4. 既存 labeled JSONL の canonical セットと差分 → 未知誌リスト

使い方:
  python3 d1_catalog_discovery.py --facet          # 空検索で1回ファセット取得（高速テスト）
  python3 d1_catalog_discovery.py --sweep          # 幅広キーワードで複数回スイープ（本番）
  python3 d1_catalog_discovery.py --diff-only      # キャッシュ済みリストから差分再計算

出力:
  /tmp/d1_discovery/catalog_journals.txt     --- 発見した全誌
  /tmp/d1_discovery/unknown_journals.txt     --- 未知誌リスト（downloader に渡す）
"""

import sys, re, json, time, argparse, random, unicodedata
from pathlib import Path
from playwright.sync_api import sync_playwright

# ---------- 設定 ----------
STATE   = Path.home() / ".gemini/antigravity/scratch/d1_state.json"
LABELED = Path.home() / "ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/labeled_v0.2.1/article_meta_labeled.jsonl"
OUT_DIR = Path("/tmp/d1_discovery")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36")
OVERLAYS = ".dh-backgroud-wrapper,.dh-background-wrapper,.dh-loading,.dh-overlay,.dh-modal-backdrop"

# 幅広キーワードスイープ用（法律・民事・刑事・労働・税・知財・行政・憲法・商法・紀要系）
SWEEP_KEYWORDS = [
    "民法",
    "刑法",
    "商法",
    "行政",
    "憲法",
    "労働",
    "税法",
    "知的財産",
    "紀要",
    "論集",
    "研究",
    "判例",
    "解説",
    "学",
]

# ---------- ユーティリティ ----------
def nfkc(s):
    return unicodedata.normalize("NFKC", s or "")

def clean_journal(raw):
    """誌名から件数表記・括弧・巻号・空白を除去して正規化。"""
    s = nfkc(raw or "")
    s = re.sub(r"\s*[\(（]\s*\d[\d,]*\s*[\)）]", "", s)  # (123) 件数除去
    s = s.lstrip("『「（(|｜ 　")
    s = re.split(r"\d", s, 1)[0]
    s = s.strip(" 　,，、。.・（(「『|｜")
    return s

def load_existing_journals(labeled_path):
    """ラベル済みJSONLから既存 canonical セットを読む。"""
    have = set()
    p = Path(labeled_path)
    if not p.exists():
        print(f"[warn] labeled ファイルが見つかりません: {labeled_path}")
        return have
    for line in p.open(encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
            for k in ("journal_canonical", "journal_raw", "journal_norm"):
                v = nfkc(r.get(k) or "")
                if v and v != "?":
                    have.add(v)
            v = clean_journal(r.get("掲載誌等") or "")
            if v:
                have.add(v)
        except Exception:
            pass
    have.discard("")
    return have

# ---------- Playwright ヘルパー ----------
def neutralize(page):
    try:
        page.evaluate(
            f"document.querySelectorAll('{OVERLAYS}').forEach(e=>{{e.style.pointerEvents='none'}})"
        )
    except Exception:
        pass

def settle(page, t=20000):
    try:
        page.wait_for_load_state("networkidle", timeout=t)
    except Exception:
        pass
    # D1 は SPA で JS レンダリングが遅い。body に何か出るまで最大 t ms 待つ
    try:
        page.wait_for_function(
            "() => (document.body.innerText || '').trim().length > 50",
            timeout=t,
        )
    except Exception:
        pass
    page.wait_for_timeout(800)
    neutralize(page)

def sleepj():
    r = random.random()
    if r < 0.80:
        time.sleep(random.uniform(4, 9))
    elif r < 0.95:
        time.sleep(random.uniform(12, 24))
    else:
        time.sleep(random.uniform(30, 55))

def click_search(page):
    """検索ボタンをJS経由でクリック（dh-btn-with-icon__text 内の親 button を叩く）。"""
    page.evaluate("""
        () => {
            const divs = Array.from(document.querySelectorAll(
                '.dh-btn-with-icon__text, [class*="btn-with-icon"]'
            ));
            for (const d of divs) {
                if ((d.innerText || d.textContent || '').trim() === '検索') {
                    const btn = d.closest('button') || d.closest('[role="button"]') || d;
                    btn.click();
                    return true;
                }
            }
            return false;
        }
    """)

def expand_facet_more(page):
    """「もっと見る」「さらに表示」ボタンを全部押して掲載誌ファセットを展開する。"""
    for _ in range(20):
        pressed = page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button, a, span'))
                    .filter(e => {
                        const t = (e.innerText || e.textContent || '').trim();
                        return (t === 'もっと見る' || t === 'さらに表示' || t === 'more' ||
                                t.includes('もっと') || t.includes('さらに')) &&
                               e.offsetParent !== null;
                    });
                if (btns.length > 0) { btns[0].click(); return true; }
                return false;
            }
        """)
        if not pressed:
            break
        page.wait_for_timeout(800)

def extract_facet_journals(page):
    """
    サイドバーの「掲載誌」ファセットから誌名を全件取得。
    HTMLクラス名に依存しない JS で抽出する。
    """
    journals = page.evaluate("""
        () => {
            // "掲載誌" というラベルを持つセクションを探す
            const allEls = Array.from(document.querySelectorAll('*'));
            let sectionEl = null;

            for (const el of allEls) {
                const t = (el.innerText || el.textContent || '').trim();
                // ちょうど「掲載誌」というテキストノードを持つ要素を探す
                if (t === '掲載誌' && el.children.length <= 2 && el.offsetParent !== null) {
                    // その親要素がセクション
                    sectionEl = el.parentElement || el;
                    break;
                }
            }

            if (!sectionEl) return [];

            // セクション内の label/li/a/span からテキストを回収
            // 数字だけのもの・"掲載誌" 自体・空は除外
            const results = [];
            const seen = new Set();
            const candidates = sectionEl.querySelectorAll('label, li, a, span, div');
            for (const c of candidates) {
                // 子要素を持たない末端テキストノードを優先
                let t = '';
                for (const node of c.childNodes) {
                    if (node.nodeType === 3) t += node.textContent;
                }
                t = t.trim();
                if (!t) t = (c.innerText || c.textContent || '').trim();
                // 数字のみ・短すぎ・既出は除外
                if (!t || t.length < 2 || /^[\\d,\\s]+$/.test(t) || t === '掲載誌') continue;
                // 件数表記を除去
                t = t.replace(/\\s*[（(]\\s*\\d[\\d,]*\\s*[）)]/g, '').trim();
                if (!t || seen.has(t)) continue;
                seen.add(t);
                results.push(t);
            }
            return results;
        }
    """)
    return {clean_journal(j) for j in (journals or []) if clean_journal(j)}

def do_search_keyword(page, keyword):
    """
    キーワード（空文字なら空検索）でD1文献編を検索し、ヒット件数を返す。
    """
    page.goto("https://mis-hs.d1-law.com/d1bun/bunsearch",
              wait_until="networkidle", timeout=45000)
    settle(page)

    if keyword:
        # フリーワード入力欄を探してキーワードを入力
        filled = page.evaluate(f"""
            () => {{
                const inputs = Array.from(document.querySelectorAll('input[type=text], input[type=search], textarea'));
                for (const inp of inputs) {{
                    if (inp.offsetParent !== null && !inp.disabled && !inp.readOnly) {{
                        inp.value = '{keyword}';
                        inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                        inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return true;
                    }}
                }}
                return false;
            }}
        """)
        if not filled:
            # フォールバック: フリーワードボタンで入力欄を追加してから入力
            try:
                page.get_by_text("フリーワード", exact=True).first.click()
                page.wait_for_timeout(600)
                page.locator("input[name='bunFreeWord'], input[name='freeword']").first.fill(keyword)
            except Exception as e:
                print(f"  [warn] キーワード入力失敗: {e}")

    page.wait_for_timeout(500)
    click_search(page)

    # 検索結果が描画されるまで待つ（「N件」か「0件」が出るまで）
    try:
        page.wait_for_function(
            r"() => /\d+\s*件/.test(document.body.innerText || '')",
            timeout=20000,
        )
    except Exception:
        pass
    page.wait_for_timeout(800)
    neutralize(page)

    url = page.url
    body = page.evaluate("() => document.body.innerText") or ""

    # セッション切れ検出（ログインページへのリダイレクト）
    if "login" in url.lower() or "ログイン" in body[:300] or "サインイン" in body[:300]:
        print(f"  [error] セッション切れ（ログインページにリダイレクト）: {url}")
        print(f"  [hint]  ~/.gemini/antigravity/scratch/d1_state.json を更新してください")
        return 0

    m = re.search(r"([0-9,]+)\s*件", body)
    total = int(m.group(1).replace(",", "")) if m else 0
    if total == 0:
        print(f"  [debug] URL: {url}")
        print(f"  [debug] body(先頭300): {body[:300].strip()!r}")
    return total

# ---------- コア ----------
def sweep_facets(page, keywords, save_html=None):
    """
    キーワードリストを順に検索し、各検索の掲載誌ファセットを集積する。
    新規誌が出なくなったら早期終了。
    """
    all_journals = set()

    for i, kw in enumerate(keywords):
        label = f'"{kw}"' if kw else "（空検索）"
        print(f"\n  [{i+1}/{len(keywords)}] キーワード: {label}")

        total = do_search_keyword(page, kw)
        print(f"  ヒット件数: {total}")

        if total == 0:
            print("  → 0件、スキップ")
            continue

        # 50件表示に切替（より多くのファセット値が出る場合あり）
        try:
            page.select_option("select[name=dispNum]", "50")
            settle(page)
        except Exception:
            pass

        # ファセット「もっと見る」を展開
        expand_facet_more(page)

        # ファセットから誌名抽出
        found = extract_facet_journals(page)
        if not found:
            print("  [warn] 掲載誌ファセットが空（セクション未検出、またはサイドバー非表示）")
            if save_html:
                try:
                    Path(save_html).write_text(page.content(), encoding="utf-8")
                    print(f"  [debug] HTML を保存しました → {save_html}")
                except Exception as e:
                    print(f"  [debug] HTML 保存失敗: {e}")
        new_count = len(found - all_journals)
        all_journals |= found
        print(f"  ファセット取得: {len(found)} 件 / 新規: {new_count} 件 / 累計: {len(all_journals)}")

        if i > 0 and new_count == 0:
            print("  → 新規なし、以降スキップ検討")

        if i < len(keywords) - 1:
            sleepj()

    return all_journals

# ---------- diff ----------
def compute_diff(found_all, labeled_path):
    existing = load_existing_journals(labeled_path)
    unknown = {nfkc(j) for j in found_all if nfkc(j) and nfkc(j) not in existing}
    return unknown, existing

def write_results(found, unknown):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sorted_found = "\n".join(sorted(found))
    (OUT_DIR / "catalog_journals.txt").write_text(sorted_found, encoding="utf-8")
    (OUT_DIR / "all_found_journals.txt").write_text(sorted_found, encoding="utf-8")
    (OUT_DIR / "unknown_journals.txt").write_text(
        "\n".join(sorted(unknown)), encoding="utf-8"
    )
    print(f"\n=== 結果 ===")
    print(f"ファセットで発見した誌: {len(found)}")
    print(f"既存canonical との差分（未知誌）: {len(unknown)}")
    print(f"未知誌リスト → {OUT_DIR}/unknown_journals.txt")
    print(f"\n--- 未知誌（上位50） ---")
    for j in sorted(unknown)[:50]:
        print(f"  {j}")
    if len(unknown) > 50:
        print(f"  ... 他 {len(unknown)-50} 誌")

# ---------- メイン ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--facet",     action="store_true", help="空検索1回だけファセット取得（テスト）")
    ap.add_argument("--sweep",     action="store_true", help="複数キーワードでスイープ（本番）")
    ap.add_argument("--diff-only", action="store_true", help="catalog_journals.txt から差分だけ再計算")
    ap.add_argument("--labeled",   default=str(LABELED))
    ap.add_argument("--save-html", metavar="PATH",
                    help="ファセット空のときに結果ページHTMLをここへ保存（デバッグ用）")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # diff-only: キャッシュから再計算
    if args.diff_only:
        cache = OUT_DIR / "catalog_journals.txt"
        if not cache.exists():
            print(f"[error] {cache} がありません。先に --facet か --sweep を実行してください。")
            sys.exit(1)
        found = {l.strip() for l in cache.read_text(encoding="utf-8").splitlines() if l.strip()}
        unknown, _ = compute_diff(found, args.labeled)
        write_results(found, unknown)
        return

    # --facet は "民法" 1キーワードで動作確認（空検索はD1フォームが実行しない場合がある）
    keywords = ["民法"] if args.facet else SWEEP_KEYWORDS

    with sync_playwright() as p:
        b = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        ctx = b.new_context(
            storage_state=str(STATE),
            viewport={"width": 1400, "height": 1000},
            user_agent=UA,
        )
        try:
            ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            )
        except Exception:
            pass
        pg = ctx.new_page()

        all_found = sweep_facets(pg, keywords, save_html=args.save_html)
        b.close()

    unknown, _ = compute_diff(all_found, args.labeled)
    write_results(all_found, unknown)

if __name__ == "__main__":
    main()
