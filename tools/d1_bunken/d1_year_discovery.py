#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D1文献編 年別スイープ → 未知雑誌の発掘

【戦略】
  年フィルタ（発行年月日）のみで検索 → 各年の先頭N頁・末尾N頁をRTFで取得 →
  掲載誌等を抽出 → 既存canonical差分 → 未知誌リスト

  RTFは一時フォルダ（/tmp/d1_discovery/）に格納し、永続データには混入しない。
  downloader は使わず独自にRTF1頁ずつ取得（年単位フォルダへのwrite禁止を守る）。

使い方:
  python3 d1_year_discovery.py --probe 2024          # 2024年1頁目だけ確認（動作テスト）
  python3 d1_year_discovery.py --sweep               # 2015-2024 全年スイープ
  python3 d1_year_discovery.py --sweep --from 2010 --to 2024 --pages 8
  python3 d1_year_discovery.py --diff-only           # RTFスイープ済みの場合、差分だけ再計算

出力:
  /tmp/d1_discovery/unknown_journals.txt  --- 未知誌リスト（1行1誌）
  /tmp/d1_discovery/all_found_journals.txt --- 年スイープで発見した全誌（参考）
  /tmp/d1_discovery/<year>/p001.rtf 等   --- 中間RTF（差分計算後に消してよい）
"""

import sys, re, json, time, math, argparse, random, unicodedata
from pathlib import Path
from playwright.sync_api import sync_playwright

try:
    from striprtf.striprtf import rtf_to_text as _rtf_to_text
except ImportError:
    _rtf_to_text = None

# ---------- 設定 ----------
STATE   = Path.home() / ".gemini/antigravity/scratch/d1_state.json"
LABELED = Path.home() / "ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/labeled_v0.2.1/article_meta_labeled.jsonl"
OUT_DIR = Path("/tmp/d1_discovery")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36")

DEFAULT_FROM = 2015
DEFAULT_TO   = 2024
DEFAULT_PAGES = 5   # 各年の先頭N頁 + 末尾N頁（計最大2N頁/年）

OVERLAYS = ".dh-backgroud-wrapper,.dh-background-wrapper,.dh-loading,.dh-overlay,.dh-modal-backdrop"

# ---------- ユーティリティ ----------
def nfkc(s):
    return unicodedata.normalize("NFKC", s or "")

def etc_journal(raw):
    """掲載誌等フィールドから誌名本体を切り出す（巻号・年号を除去）。"""
    s = nfkc(raw).lstrip("『「（(|｜ ")   # RTF列区切り | も除去
    s = re.split(r"\d", s, 1)[0]
    return s.strip(" 　,，、。.・（(「『|｜")

def load_existing_journals(labeled_path):
    """ラベル済みJSONLから既存 canonical 誌名セットを読む。"""
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
            # 掲載誌等 からも
            v = etc_journal(r.get("掲載誌等") or "")
            if v:
                have.add(v)
        except Exception:
            pass
    have.discard("")
    return have

def extract_journals_from_rtf(rtf_text):
    """RTFテキストから掲載誌等の値を全件抽出。"""
    journals = set()
    for m in re.finditer(r"【掲載誌等】([^\n【]+)", rtf_text):
        j = etc_journal(m.group(1))
        if j:
            journals.add(j)
    return journals

# ---------- Playwright ヘルパー ----------
def neutralize(page):
    try:
        page.evaluate(
            f"document.querySelectorAll('{OVERLAYS}').forEach(e=>{{e.style.pointerEvents='none'}})"
        )
    except Exception:
        pass

def settle(page, t=20000):
    try: page.wait_for_load_state("networkidle", timeout=t)
    except Exception: pass
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

def _enable_date_condition(page):
    """発行年月日条件を追加してフィールドを有効化する。"""
    page.get_by_text("検索条件を追加").first.click()
    page.wait_for_timeout(1500)
    neutralize(page)
    # ドロップダウン内の「発行年月日」を JS で探してクリック
    # （ページ上に同名ラベルが既に存在するため get_by_text.first だと誤クリックする）
    clicked = page.evaluate("""
        () => {
            const candidates = Array.from(document.querySelectorAll(
                'li, a, button, [role="option"], [role="menuitem"], .dh-search-condition__item'
            )).filter(e => {
                const t = (e.innerText || e.textContent || '').trim();
                return t === '発行年月日' && e.offsetParent !== null;
            });
            if (candidates.length > 0) { candidates[0].click(); return true; }
            return false;
        }
    """)
    if not clicked:
        page.get_by_text("発行年月日", exact=True).last.click()
    page.wait_for_timeout(1200)

def _fill_date_fields(page, year):
    """発行年月日フィールドに年の開始〜終了を入力する。Tab でピッカーを閉じながら進む。"""
    pairs = [
        ("bunSearchFromPublishY", str(year)), ("bunSearchFromPublishM", "1"),  ("bunSearchFromPublishD", "1"),
        ("bunSearchToPublishY",   str(year)), ("bunSearchToPublishM",   "12"), ("bunSearchToPublishD",   "31"),
    ]
    try:
        page.locator("input[name='bunSearchFromPublishY']").wait_for(state="enabled", timeout=8000)
    except Exception:
        pass
    for name, val in pairs:
        loc = page.locator(f"input[name='{name}']")
        try:
            loc.click()
            loc.fill(val)
            page.keyboard.press("Tab")   # ピッカードロップダウンを閉じてフォーカスを移す
            page.wait_for_timeout(150)
        except Exception:
            page.evaluate(
                f"() => {{ const el=document.querySelector(\"input[name='{name}']\"); "
                f"if(el){{ el.removeAttribute('disabled'); el.value='{val}'; }} }}"
            )

def search_by_year(page, year):
    """発行年月日フィルタで year 年の全件を検索し、総件数を返す。"""
    page.goto("https://mis-hs.d1-law.com/d1bun/bunsearch",
              wait_until="networkidle", timeout=45000)
    settle(page)

    _enable_date_condition(page)
    _fill_date_fields(page, year)

    # フィールド値を確認（デバッグ）
    vals = page.evaluate("""() => ({
        fromY: document.querySelector("input[name='bunSearchFromPublishY']")?.value,
        fromM: document.querySelector("input[name='bunSearchFromPublishM']")?.value,
        fromD: document.querySelector("input[name='bunSearchFromPublishD']")?.value,
        toY:   document.querySelector("input[name='bunSearchToPublishY']")?.value,
        toM:   document.querySelector("input[name='bunSearchToPublishM']")?.value,
        toD:   document.querySelector("input[name='bunSearchToPublishD']")?.value,
    })""")
    print(f"  [debug] date fields: {vals}")

    neutralize(page)
    page.wait_for_timeout(400)

    # 検索ボタン: 親 <button> を JS で直接 click（div テキストでなく button 要素を叩く）
    page.evaluate("""
        () => {
            const divs = Array.from(document.querySelectorAll('.dh-btn-with-icon__text, [class*="btn"]'));
            for (const d of divs) {
                if ((d.innerText || d.textContent || '').trim() === '検索') {
                    const btn = d.closest('button') || d.closest('[role="button"]') || d;
                    btn.click();
                    return;
                }
            }
        }
    """)
    settle(page)

    body = page.text_content("body") or ""
    m = re.search(r"([0-9,]+)\s*件", body)
    total = int(m.group(1).replace(",", "")) if m else 0

    # 50件表示に切替
    try:
        page.select_option("select[name=dispNum]", "50")
        settle(page)
    except Exception as e:
        print(f"  [warn] 50件表示切替失敗: {e}")

    return total

def download_page_rtf(ctx, page, pg_num, year_dir):
    """現在の検索結果ページ pg_num のRTFを取得して保存。掲載誌等セットを返す。"""
    out = year_dir / f"p{pg_num:03d}.rtf"
    if out.exists():
        # 冪等スキップ
        if _rtf_to_text:
            text = _rtf_to_text(out.read_text(encoding="utf-8", errors="replace"))
            return extract_journals_from_rtf(text)
        return set()

    journals = set()
    try:
        page.get_by_text("すべて選択", exact=True).first.click(); page.wait_for_timeout(800)
        neutralize(page)
        with ctx.expect_page(timeout=25000) as pinfo:
            page.get_by_text("印刷ダウンロード").first.click()
        dlp = pinfo.value
        dlp.wait_for_load_state("networkidle"); dlp.wait_for_timeout(1200)
        with dlp.expect_download(timeout=45000) as dinfo:
            dlp.get_by_role("button", name="ダウンロード").first.click()
        dl = dinfo.value
        dl.save_as(str(out))
        dlp.close()
        page.get_by_text("クリア", exact=True).first.click(); page.wait_for_timeout(500)
    except Exception as e:
        print(f"  [warn] p{pg_num} RTF取得失敗: {e}")
        return journals

    if _rtf_to_text and out.exists():
        text = _rtf_to_text(out.read_text(encoding="utf-8", errors="replace"))
        journals = extract_journals_from_rtf(text)
    return journals

def goto_page(page, target, current):
    """ページ送りで target 頁へ移動（current から順送り or 末尾からアクセス）。"""
    # シンプル実装: 次頁ボタンで送る（current → target が近い場合）
    # 末尾は last_page ボタンで飛ぶ
    diff = target - current
    if diff == 0:
        return True
    if diff == 1:
        try:
            nxt = page.locator("a[aria-label='次のページ'], a.dh-pagenation__item--next").first
            if nxt.count():
                nxt.click(); settle(page); return True
        except Exception:
            pass
    # ページ番号リンクをクリック
    try:
        page.get_by_text(str(target), exact=True).first.click(timeout=5000)
        settle(page); return True
    except Exception:
        return False

# ---------- コア: 1年分のスイープ ----------
def sweep_year(ctx, pg, year, n_pages, out_base):
    """year 年を検索し、先頭 n_pages 頁 + 末尾 n_pages 頁 のRTFから掲載誌等を収集。"""
    year_dir = out_base / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    total = search_by_year(pg, year)
    max_pg = math.ceil(total / 50) if total else 0
    print(f"  {year}: 総件数={total} 最大{max_pg}頁")
    if max_pg == 0:
        return set()

    target_pages = sorted(set(
        list(range(1, min(n_pages + 1, max_pg + 1))) +
        list(range(max(1, max_pg - n_pages + 1), max_pg + 1))
    ))
    print(f"  取得予定頁: {target_pages}")

    all_journals = set()
    cur = 1
    for tp in target_pages:
        if tp != cur:
            ok = goto_page(pg, tp, cur)
            if not ok:
                print(f"  [warn] p{tp} へ移動失敗")
                continue
            cur = tp
        jj = download_page_rtf(ctx, pg, tp, year_dir)
        print(f"    p{tp}: 誌名 {len(jj)} 件")
        all_journals |= jj
        cur = tp
        sleepj()

    return all_journals

# ---------- diff ----------
def compute_diff(found_all, labeled_path):
    existing = load_existing_journals(labeled_path)
    unknown = set()
    for j in found_all:
        j2 = nfkc(j)
        if j2 and j2 not in existing:
            unknown.add(j2)
    return unknown, existing

# ---------- メイン ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", metavar="YEAR", type=int, help="指定年の1頁目だけ確認")
    ap.add_argument("--sweep", action="store_true", help="全年スイープ")
    ap.add_argument("--diff-only", action="store_true", help="既存RTFから差分だけ再計算")
    ap.add_argument("--from", dest="from_year", type=int, default=DEFAULT_FROM)
    ap.add_argument("--to",   dest="to_year",   type=int, default=DEFAULT_TO)
    ap.add_argument("--pages", type=int, default=DEFAULT_PAGES,
                    help="各年の先頭/末尾 N 頁ずつ（default=5）")
    ap.add_argument("--labeled", default=str(LABELED))
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # diff-only: RTFから再計算
    if args.diff_only:
        found = set()
        for rtf in OUT_DIR.rglob("*.rtf"):
            if _rtf_to_text:
                text = _rtf_to_text(rtf.read_text(encoding="utf-8", errors="replace"))
                found |= extract_journals_from_rtf(text)
        unknown, existing = compute_diff(found, args.labeled)
        _write_results(found, unknown)
        return

    years = [args.probe] if args.probe else list(range(args.from_year, args.to_year + 1))
    n_pages = 1 if args.probe else args.pages

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"])
        ctx = b.new_context(storage_state=str(STATE), viewport={"width":1400,"height":1000},
                            user_agent=UA, accept_downloads=True)
        try:
            ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            )
        except Exception:
            pass
        pg = ctx.new_page()

        all_found = set()
        for year in years:
            print(f"\n=== {year} 年スイープ ===")
            jj = sweep_year(ctx, pg, year, n_pages, OUT_DIR)
            all_found |= jj
            print(f"  {year} 完了: 累計発見誌={len(all_found)}")
            if len(years) > 1:
                time.sleep(random.uniform(20, 40))  # 年間クールダウン

        b.close()

    unknown, existing = compute_diff(all_found, args.labeled)
    _write_results(all_found, unknown)

def _write_results(found, unknown):
    (OUT_DIR / "all_found_journals.txt").write_text(
        "\n".join(sorted(found)), encoding="utf-8"
    )
    (OUT_DIR / "unknown_journals.txt").write_text(
        "\n".join(sorted(unknown)), encoding="utf-8"
    )
    print(f"\n=== 結果 ===")
    print(f"年スイープで発見した誌: {len(found)}")
    print(f"既存canonical との差分（未知誌）: {len(unknown)}")
    print(f"未知誌リスト → {OUT_DIR}/unknown_journals.txt")
    print(f"\n--- 未知誌（上位50） ---")
    for j in sorted(unknown)[:50]:
        print(f"  {j}")
    if len(unknown) > 50:
        print(f"  ... 他 {len(unknown)-50} 誌")

if __name__ == "__main__":
    main()
