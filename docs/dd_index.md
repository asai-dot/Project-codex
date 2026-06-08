# DD 全体インデックス（MECE 構造マップ）

**目的**: 事務所AI化プロジェクトの「DD（設計レビュー／構築タスク）」は複数が並走し、
1つのDDが複数のデータオブジェクトに跨る（＝複層する）。本書は**その複層をほどき、
「データオブジェクトを縦軸の正本」に固定**して、各DD／ワークストリーム（PR）を
**ちょうど1箇所へ MECE に割り付けた索引**である。

- これは **構造の正本**（何が・どういう順で・どこに属すか）。固定の表示順を持つ。
- **実行・運用の最新進捗**（runtime_status）は別軸 → パイプラインダッシュボード
  （合言葉 `/dd`）が live に出す。本書は「地図」、ダッシュボードは「現在地」。
- 本書中の件数は各ワークストリームの**自己申告の代表値**（出所はPR）。確定実数は
  `/dd`（snapshot）を参照。lifecycle 語（accepted/canonical…）とは別軸。

---

## 0. 全体構造（2本柱 ＋ 横断層）

```
                ┌──────────────── 静的データベース（リファレンス：蔵書 canonical / 法情報） ────────────────┐
  取得 ──▶ 加工 ──▶ 接合 ──▶ 索引/反映 ──▶ 活用
   A1 書誌   A2 詳細目次   A3 法律用語辞書   A4 著者・人物   A5 法令(e-Gov)   A6 判例・引用グラフ
                └──────────────────────────────── 6 オブジェクト ───────────────────────────────────┘

                ┌──────────── 動的データベース（運用ナレッジ：案件 / メール / 時系列） ───────────┐
   B1 案件(matter)   B2 メール/Gmail   B3 lawtime   B4 GPT往復ナレッジ
                └──────────────────────────────────────────────────────────────────────────┘

  ── 横断層（オブジェクトではなく仕組み・規律）──
   C1 品質ガバナンス(Supabase)   C2 GPTお目付け監査レーン   C3 進捗可視化(/dd)   C4 チーム/Codex運用
```

**読み方の原則（MECE）**
- 軸①＝**静的DB / 動的DB / 横断層**（3区分、重なりなし）。
- 軸②＝静的DBは **6オブジェクト**で割る。各オブジェクトに属するDD/PRと進捗を置く。
- 1つのDDが複数オブジェクトに跨る場合（#8 論文抽出, #2 学陽 等）は、**跨り先の各
  オブジェクトに「その部分だけ」を分解して記載**する（複層させない）。
- 末尾 §7 の対応表が「全PRがちょうど1次配置を持つ」検算（漏れ・重複なし）。

---

## 1. 静的データベース ── 6オブジェクト（表示順＝取得→活用の依存順）

### A1. 書誌 canonical（biblio / books）
- **定義**: 蔵書の正本書誌（5,206冊）。ISBN/book_id を背骨に、NDL正本照合で正規化。
- **担当**: legallib→biblio 取込設計（PR #4 / `legal-library-metadata-impact`）、
  NDL正本照合（pipeline `ndl_canonical`）。**活用**: 購入レコメンド（PR #7）。
- **現状（申告）**: 蔵書 5,206冊ベース。legaldb v0.5 設計が監査整合待ち。
- **次の一手**: legallib 生JSON実フィールド確定 → biblio ローダ確定。

### A2. 詳細目次 TOC（bib_toc ノード）＋ 横断検索/ビューワー
- **定義**: 章節・ページ単位の目次ノード。蔵書の「中身」インデックスと4図書館横断着地。
- **担当**: legallib詳細TOC×canonical接合（PR #5 / `legallib-integration-design`、
  不変条件＝誤マージ0・人手/NDL目次を劣化させない）、横断検索/ビューワー（PR #6 /
  `toc-search-rag`）。
- **現状（申告）**: TOCノード **124k+〜552,544**（DB規模）。接合は dryrun→review→apply の
  段階設計、検索索引はページ・章節パス・出典入りに再構築済。
- **跨り注記**: 論文entity抽出（#8）の「目次→{title,authors}分解」は A2 由来だが、
  著者は A4、法令/判例リンクは A5/A6 へ分解（下記）。

### A3. 法律用語辞書（terms）
- **定義**: 法律用語の見出し語＋定義の正本。JLT・学陽・有斐閣の三点測量で確度を担保。
- **担当**: 用語辞書クリーニング基盤（PR #2 / `gakuyo-headless-migrate`：JLT v19.0
  権威見出し 3,869・学陽 all_entries 2,684・三点測量 union 15,654 / core 922・読み訂正37件）、
  JLT v19.0 Box着地確認（PR #1 / `box-dispatch-storage`：8ファイル byte-exact）。
- **現状（申告）**: 学陽 554件正規化・7,058引用リンク。三点測量済。
- **次の一手**: 三点測量の core を canonical 用語へ昇格（owner ratify 要）。

### A4. 著者・人物（authority.person）
- **定義**: 著者の名寄せ正本（NFKC・敬称/所属除去 → author_key）。横断検索/引用の鍵。
- **担当**: 論文entity抽出の**著者正規化部分**（PR #8 / `journal-article-legal-linking`）。
- **現状（申告）**: authority.person 128,081（5,647人が複数別名＝名寄せ ground truth）。
  本PRの author_normalize は既存 normalized_key より精緻。
- **次の一手**: 生 `legallib_dl/*.json`（番頭Mac）での本番スイープ。

### A5. 法令（statute / e-Gov）
- **定義**: 条文参照を e-Gov 法令へ正規リンク（枝番・漢数字・全角対応）。引用グラフの芽。
- **担当**: 論文抽出の**法令リンク部分**（PR #8）、学陽の **e-Gov 同期部分**（PR #2）。
- **現状（申告）**: e-Gov定義 534（13法令）／学陽 見出し語↔条文 1,731リンク（326見出し語）／
  e-Gov条見出し 4,367条・3,267見出し（7法令）／DB全体 条文参照 10,211。
- **次の一手**: 422号雑誌の本番スイープで mention をフル化。

### A6. 判例・引用グラフ（precedent / case ＋ citations ＋ RAG）
- **定義**: 判例の正本キー（和暦・事件番号・裁判所）と 文献↔判例↔法令 の引用グラフ、③RAG。
- **担当**: 知識グラフ（PR #11 / `kg-lit-precedent-rag`）、論文抽出の**判例リンク部分**（PR #8）。
- **現状（申告）**: case_citations 17,259件（被覆率 40%→100% を地名再抽出で実証）。
  judgments 3層着地（内部PD→裁判所HTML→ベンコム）。
- **次の一手**: 本番フル17,259件の `--from-raw` 実走で被覆率/衝突を確定。

---

## 2. 動的データベース ── 運用ナレッジ（案件 / メール / 時系列）

### B1. 案件（matter）
- **定義**: 事件・相談の正本。Salesforce ID を背骨に Box/Gmail を横断紐付け。
- **担当**: 案件データ紐付け（PR #3 / `data-linking-progress`）、pipeline `matter_resolution`。
- **現状（申告）**: crosswalk 3システム横断表（sf_id 背骨）、別名候補154・非案件41、
  GPT CASELINK 監査 PASS_WITH_NOTES、巻戻し台帳 append-only。

### B2. メール / Gmail
- **定義**: 案件ラベル付きメールの紐付け。B1 と一体で運用。
- **担当**: 同上（PR #3）。
- **現状（申告）**: 案件ラベル 1,181件を Salesforce ID 付きで構造化。

### B3. lawtime（時系列）
- **定義**: lawtime v0.1 の DD 成果（時点・時系列ナレッジ）。
- **担当**: pipeline `lawtime_dd`（DD-LAWTIME-001）。**現状**: from_gpt RESULT 待ち。

### B4. GPT往復ナレッジ（DD knowledge）
- **定義**: to_gpt→from_gpt の往復で得られる設計知（lawtime/matter 等の上流）。
- **担当**: pipeline `gpt_dd_roundtrip`。**現状**: roundtrip の pending/stale で可視化。

> 動的DBは静的DBより未構築。B1/B2 は設計＋紐付け実装が進行、B3/B4 は GPT 往復に依存。

---

## 3. 横断層 ── 仕組み・規律（オブジェクトではない）

- **C1. 品質ガバナンス（Supabase）** — PR #9 / `supabase-data-quality-strategy`。
  clean-only・環境分離（staging/prod）・門番二段・「DBを一人歩きさせない（正本はGit）」。
  静的DB全オブジェクトの**投入規律**。現状 DD-LAWTIME v0.2 accept 待ちで一部 blocked。
- **C2. GPT お目付け監査レーン** — PR #10 `audit-lane-implementation` / #12 `gpt-pro-audit-loop`
  / #14 `gpt-queue-audit`。to_gpt/from_gpt/processed の三点照合、台帳、**反映キュー**
  （監査結果≠正本化）、キュー陳腐化検出。全DDの**承認動線**。
- **C3. 進捗可視化（/dd）** — PR #15 / `pipeline-collect-validation`（本ブランチ）。
  manifest+snapshot から runtime_status を描画。合言葉 `/dd`・Mac 日次採取（launchd 9:00）。
- **C4. チーム / Codex 運用** — PR #13 / `codex-setup-docs`。`AGENTS.md`・team-scheme・
  Data DoD・監査の独立性。全DDの**作業規律**。

---

## 4. オブジェクト間の流れ（依存パイプライン）

```
A1 書誌 ─┬─▶ A2 詳細目次(接合) ─┬─▶ A6 判例・引用グラフ ◀─ A5 法令(e-Gov) ◀─ A3 用語辞書
         │                      └─▶ (横断検索/ビューワー)        ▲
         └─▶ A4 著者・人物 ──────────────────────────────────────┘
   （取得 → 加工/抽出 → 接合 → 索引/反映 → 活用。C1 が各段の投入を門番、C2 が設計を承認）
```

---

## 5. いま見るべき要点（横断サマリ）

- **最も積み上がっている**: A2 詳細目次（接合設計＋横断検索）と A5/A6（法令・判例リンクが
  本番データで成立）。A3 用語辞書も三点測量まで到達。
- **承認待ちで止まりがち**: C1 ガバナンス・各オブジェクトの canonical 昇格は **owner ratify**
  と **GPT監査(C2)** がゲート。「作った≠正本」をここで律速。
- **未構築寄り**: 動的DB（B3 lawtime / B4 GPT往復）と、A1→biblio ローダの実フィールド確定。

---

## 6. 関連する既存 DD

- `canonicalindex v0.1 DDINDEXDISPO`（GPTキュー #14 で未返却検出）= 「索引の扱い」DD。
  本書（dd_index）はその構造面の整理に対応。GPT お目付けの返却を待って整合させる。

---

## 7. ワークストリーム → 一次配置 対応表（MECE 検算）

| PR | ブランチ | 一次オブジェクト | 跨り（分解先） |
|---|---|---|---|
| #1 | box-dispatch-storage | A3 用語辞書 | — |
| #2 | gakuyo-headless-migrate | A3 用語辞書 | A5 法令（e-Gov同期） |
| #3 | data-linking-progress | B1 案件 | B2 メール/Gmail |
| #4 | legal-library-metadata-impact | A1 書誌 | — |
| #5 | legallib-integration-design | A2 詳細目次 | — |
| #6 | toc-search-rag | A2 詳細目次（検索/ビューワー） | — |
| #7 | purchase-recommendations-topic | A1 書誌（活用層） | A2 |
| #8 | journal-article-legal-linking | A4 著者 | A2(分解)・A5 法令・A6 判例 |
| #9 | supabase-data-quality-strategy | C1 ガバナンス | （全オブジェクトの投入規律） |
| #10 | audit-lane-implementation | C2 監査レーン | — |
| #11 | kg-lit-precedent-rag | A6 判例・引用グラフ | A5 法令 |
| #12 | gpt-pro-audit-loop | C2 監査レーン | — |
| #13 | codex-setup-docs | C4 チーム運用 | — |
| #14 | gpt-queue-audit | C2 監査レーン | — |
| #15 | pipeline-collect-validation | C3 可視化 | — |

→ 15ワークストリームが **静的6オブジェクト(A) / 動的4(B) / 横断4(C)** に漏れなく
重複なく配置（複層は「跨り」列で分解して明示）。

---

_v0.1（構造の初版）。6オブジェクトの切り方・表示順・跨りの分解粒度は提案。実体に合わせて
育てる（オブジェクト追加・statute と判例の引用グラフ統合など）。runtime 進捗は `/dd`。_
