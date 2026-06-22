# HANDOFF — D1文献編 取得の「完走→確定」一周（Mac Claude Code 向け）

対象: D1-Law 文献編・雑誌別記事メタの再取得を**完走→パース→確定**まで回す。
状況: 2026-06-19 に 16誌の冪等再取得が **download 完走**。残りは下記 STEP 1〜3。
守秘: 件数/構造のみ。本文・生引用は扱わない。

> 大原則（必ず守る）
> - やってよいのは **取得（追加のみ・元データ改変なし）／パース／読み取り確認** だけ。
> - 禁止（owner-gated・勝手にやらない）: DB投入 / canonical昇格 / index backfill /
>   Salesforce書戻し / 外部共有・公開。
> - ダウンローダは**冪等**。止まっていたら同じコマンドを再実行すれば続きから。
>   **単一書き手**で（多重起動しない）。

---

## パス

- ダウンローダ: `~/.gemini/antigravity/scratch/d1_bunken_downloader.py`
  - 使い方: `python3 d1_bunken_downloader.py "誌名" <ページ数>`（`0`=全ページ・冪等）
  - ログインセッション: `~/.gemini/antigravity/scratch/d1_state.json`（生きている必要）
  - 出力: `~/alo-ai/work/d1law_dl/bunken/<誌>/pNNNN_*.rtf` ＋ `manifest.jsonl`
- パーサ: `ALOBookDX/事務所内本棚DX化計画/scripts/d1_bunken_parse_all.py`（引数なし）
  - 出力: `build/d1_bunken_article_meta_20260611/article_meta_all.jsonl` ＋ `summary.json`
- 優先キューJSON: `d1_bunken_journal_acquisition_priority_20260612.json`
  （Box `データ種別分離_20260611/_inventory/` もしくは `build/` 配下）

---

## STEP 1 ｜ パーサを1回（最終件数の確定・最優先）

```bash
python3 ALOBookDX/事務所内本棚DX化計画/scripts/d1_bunken_parse_all.py
python3 -c "import json;d=json.load(open('ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/summary.json'));print('unique_articles=',d.get('unique_articles'))"
```

→ `unique_articles` を owner（リモートClaude）へ報告。到達率（前回 160,351 / 35.7% → ?）を確定する。

## STEP 2 ｜ 総件数=0 だった5誌の再投入（誌名表記差・追加のみ）

2026-06-19 実測で 0件だった: `別冊法学教室基本判例シリーズ` / `私法` / `季刊刑事弁護` /
`公正取引`(既存1頁) / `登記研究`(既存1頁)。原因はほぼ誌名表記差。

```bash
DL=~/.gemini/antigravity/scratch/d1_bunken_downloader.py

# (a) 丸めすぎ → 元の2誌名に分割
python3 $DL "基本判例解説シリーズ" 0
python3 $DL "法学教室基本判例" 0

# (b) variant 試行
python3 $DL "刑事弁護" 0

# (c) 公正取引／登記研究：過去に1頁取れている＝別誌名でヒット済み。
#     成功時の検索語を manifest から復元してから再投入
grep -h '"query"' ~/alo-ai/work/d1law_dl/bunken/公正取引*/manifest.jsonl 2>/dev/null | head
grep -h '"query"' ~/alo-ai/work/d1law_dl/bunken/登記研究*/manifest.jsonl 2>/dev/null | head
```

> `私法`（学会誌）は article-level 非収録の可能性あり。D1側の正式誌名を1度だけ目視確認して判断（深追い不要）。

## STEP 3 ｜ 金判（金融・商事判例）の未キュー確認

```bash
PRI=$(find "$HOME" "$HOME/Library/CloudStorage" -name 'd1_bunken_journal_acquisition_priority_*.json' 2>/dev/null | head -1); DL="$HOME/alo-ai/work/d1law_dl/bunken"; python3 - "$PRI" "$DL" <<'PY'
import json,sys,os
pri,dl=sys.argv[1],sys.argv[2]
def walk(o):
    if isinstance(o,dict):
        for v in o.values(): yield from walk(v)
    elif isinstance(o,list):
        for v in o: yield from walk(v)
    elif isinstance(o,str): yield o
pn={s for s in walk(json.load(open(pri))) if '金' in s} if pri and os.path.exists(pri) else set()
dn={d for d in os.listdir(dl) if '金' in d} if os.path.isdir(dl) else set()
print("優先JSON『金』:", *sorted(pn) or ["(なし/JSON未検出)"])
print("DL済『金』:", *sorted(dn) or ["(なし)"])
print(">>> 未取得 =", sorted(pn-dn) or "(差分なし)")
PY
```

→ `金融・商事判例`/`金判` が「未取得」に出たら `python3 $DL "金融・商事判例" 0` で追加。

---

## 名寄せ宿題（反映はしない・メモのみ下流レーンへ）

- 「タイム」フォルダ = **判例タイムズ**（217頁）の別名マップ。
- STEP 2 で誌名修正した誌の対応表。

## 最後に報告（5行）

1. 完走/未完の誌
2. `summary.json` の `unique_articles` と到達率（旧35.7% → 新?%）
3. 金判: キュー有無と対応
4. 表記差で直した誌
5. owner判断が要る点（あれば）
