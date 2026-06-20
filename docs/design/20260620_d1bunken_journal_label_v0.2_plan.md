# PLAN — D1文献編 誌名ラベル付与(v0.2) と 取得残差クローズ

- date_jst: 2026-06-20
- author: Claude (remote) ＋ 浅井（Mac Studio 実行）
- 前提: 取得フェーズは完走・パース確定済み（**282,761件 / 62.9%**, §状況報告 2026-06-19）。
- このPLANの目的: 「Mac環境に戻ってから」何を・どの順で・どこまでやれば**このスレが集結するか**を固定する。

---

## 0. このスレの役割（スコープの線引き）

- **このスレ（remote Claude）= 計画・設計・ドキュメント・Mac結果の検証**を担う頭脳側。
- **実行（パーサ走行・診断・再取得）= Mac側**（`~/alo-ai` / `~/.gemini` / Box Drive がある環境）。
- リモートからは jsonl もパーサ本体も触れない。よって「Macが結果を貼る → remoteが判定・設計更新・コミット」を1サイクルとして回す。

---

## 1. ゴール（このスレの最終到達点）

> **D1文献メタ 282,761件に“信頼できる誌名”が付き、誌別内訳（評釈の価値順）が出せる状態にする。**

具体的には:
- `by_journal` の `?`（現 276,931件＝約98%）を**ほぼ0**にし、残差は `UNMAPPED:*` として件数把握できる。
- 誌別件数が評釈順位と整合（法律時報≈9,301 / 判例評論≈5,888 など）。
- 取得残差（0件5誌・金判）が再投入 or 判断済みでクローズ。
- 上記が **PR #30 とBox状況報告に反映**され、PRがマージ可能になる。

---

## 2. やること / やらないこと

**やる（in scope）**
- 真因の確定（診断1回）→ v0.2 ラベル付与ロジックの実装・実行・検証。
- 0件5誌の再投入（誌名表記差の解消, §8）。
- 金判（金融・商事判例）の未キュー確認 →必要なら追加取得。
- ドキュメント更新（PR #30 + Box 状況報告）。

**やらない（out of scope = 別ゲート / owner承認）**
- DB投入・canonical昇格・index backfill・Salesforce書戻し・外部共有。
- 長尾797誌の深追い（owner判断・当面保留）。
- 下流の CiNii×NDL 名寄せ統合本体（誌名IDが揃ってから別タスク）。

---

## 3. Mac復帰後の手順（S0→S4）

### S0. 真因を固める（診断・読み取りのみ）
下の「確認バンドル」を1回流し、結果を remote に貼る。→ remote が判定表で真因を確定。
```bash
PARSER="ALOBookDX/事務所内本棚DX化計画/scripts/d1_bunken_parse_all.py"
JSONL="ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/article_meta_all.jsonl"
python3 - "$JSONL" <<'PY'
import json,sys,collections
p=sys.argv[1]; keys=collections.Counter(); jvals=collections.Counter()
pathish=collections.Counter(); ex_q=ex_l=None; n=0
for l in open(p):
    r=json.loads(l); n+=1; keys.update(r.keys())
    j=str(r.get('journal','')); jvals[j]+=1
    for k in r:
        if any(t in k.lower() for t in ('path','file','dir','folder','src','source')): pathish[k]+=1
    if j in ('','?','None') and ex_q is None: ex_q=r
    if j not in ('','?','None') and ex_l is None: ex_l=r
print('records:',n); print('fields:',keys.most_common())
print('path-ish:',pathish.most_common()); print('? total:',jvals.get('?',0)+jvals.get('',0)+jvals.get('None',0))
print('journal top12:',jvals.most_common(12))
print('sample ?:',json.dumps(ex_q,ensure_ascii=False)[:900])
print('sample labeled:',json.dumps(ex_l,ensure_ascii=False)[:900])
PY
grep -nE "journal|掲載誌|誌名|\.rtf|glob|rglob|os\.walk|parent|dirname|basename|\"\?\"|'\?'" "$PARSER" | head -60
```
**判定表（真因→直し方）**
| path-ish field | パーサ挙動 | 真因 | v0.2の直し方 |
|---|---|---|---|
| 有り | — | 素材は在る | 後処理だけ（パーサ非改修） |
| 無し | 親フォルダ名を捨てて列挙 | 列挙時に誌名未記録 | 入力段で `path.parent.name` を焼く |
| 無し | フォルダ名を本文で上書き | 優先順位ミス | フォルダ名を正・本文をfallback |

### S1. v0.2 実装（ラベル付与）
原則: **誌名の一次ソース＝フォルダ名（検索語）。本文抽出は照合用に降格。**
パイプライン: `journal_raw（フォルダ名）→ normalize（NFKC・空白/中黒/括弧）→ alias_map → 優先JSONのcanonicalと突合 → journal_id付与`。
追加列: `journal_raw / journal_norm / journal_canonical / journal_id / journal_source / match_status`。
出力は**新build**（`..._labeled_YYYYMMDD/`）に。v0.1 jsonl は不変（非破壊・冪等）。
別名初期値: `タイム→判例タイムズ` ほか（S3確定分を順次追加）。

### S2. 検証（受け入れ基準＝§4）
ラベル付与後の `by_journal` を出し、`?`残数・誌別件数・総数不変を確認 → remote に貼る。

### S3. 取得残差クローズ
- 0件5誌を正式名で再投入（`基本判例解説シリーズ`/`法学教室基本判例`分割、`刑事弁護`、公正取引・登記研究はmanifestの検索語復元）。
- 金判の未キュー確認1行 →必要なら `金融・商事判例` 追加取得。
- 再取得した分はS1のラベル付与に取り込み（冪等再実行）。

### S4. ドキュメント確定
状況報告 §3/§8/§10 を「誌名付与 完了・残差クローズ」に更新 → PR #30 push ＋ Box 新バージョン（owner許可の上で）。

---

## 4. 集結条件（このスレを閉じるチェックリスト）

- [ ] **S0** 真因が判定表のどれかに確定（診断結果が貼られた）。
- [ ] **S1** v0.2 がラベル付き新build jsonl を出力（非破壊・冪等）。
- [ ] **S2-a** `by_journal` の `?` が 276,931 → **ほぼ0**（残差は `UNMAPPED:*` で件数可視）。
- [ ] **S2-b** 誌別件数が評釈順位と整合（法律時報≈9,301 / 判例評論≈5,888 等を目視確認）。
- [ ] **S2-c** `unique_articles=282,761` が**不変**（ラベル付与は件数を変えない）。
- [ ] **S3-a** 0件5誌が再投入 or 「非収録」と判断済み。
- [ ] **S3-b** 金判のキュー有無が確定（無ければ追加取得）。
- [ ] **S4** 状況報告（PR #30 + Box）が最新化、**PR #30 がマージ可能**。

→ 8項目すべて ✅ で**このスレは集結**。下流（CiNii×NDL 名寄せ統合）は別スレ・別ゲート。

---

## 5. 戻ったときの最初の1手

**S0 の確認バンドルを流して結果を貼る**だけ。あとは判定→設計確定→実装の順に remote が伴走する。

## 6. 未確定リスク（先に見えているもの）

- `私法` は article-level 非収録の可能性（誌名付与しても0件のままなら「非収録」確定）。
- Boxミラー層（`D1law/<X>/`）の `<X>` が誌名でない場合、その層だけ本文fallback＋conflict検出が要る。
- 優先JSONの canonical 名と D1表記の粒度差（別冊/シリーズ物）は突合時に手当てが要る。
