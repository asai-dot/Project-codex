# DD 全体インデックス（MECE 構造マップ）

**目的**: 事務所AI化プロジェクトの「DD（設計レビュー／構築タスク）」は複数が並走し、
1つのDDが複数のデータオブジェクトに跨る（＝複層する）。本書は**その複層をほどき、
「データオブジェクトを縦軸の正本」に固定**して、各DD／ワークストリーム（ブランチ／PR）を
**ちょうど1箇所へ MECE に割り付けた索引**である。

- これは **構造の正本**（何が・どういう順で・どこに属すか）。固定の表示順を持つ。
- **実行・運用の最新進捗**（runtime_status）は別軸 → パイプラインダッシュボード（`/dd`）。
  本書は「地図」、ダッシュボードは「現在地」。
- 件数は各ワークストリームの**自己申告の代表値**。確定実数は `/dd`（snapshot）参照。
- 分類軸の正本（浅井先生）: **静的DB＝7オブジェクト**、**動的DB＝6ソース系統**。

---

## 0. 全体構造（2本柱 ＋ 横断層）

```
■ 静的データベース（リファレンス：法情報・蔵書）── 7 オブジェクト（表示順固定）
   ① 法令      ② 判例      ③ 文献      ④ 雑誌      ⑤ 語彙      ⑥ 手続      ⑦ 書式
                          └ 書誌メタ・著者・詳細目次(TOC) は ③文献/④雑誌 のサブ

■ 動的データベース（運用：案件まわりの一次データ）── 6 ソース系統（取得元で割る）
   Ⓐ Google系   Ⓑ Salesforce系   Ⓒ Box系   Ⓓ notta(meetings)系   Ⓔ ダイヤルパッド系   Ⓕ その他
                          └ 案件(matter) は各系統が解決・収斂する「背骨」

── 横断層（オブジェクトではなく仕組み・規律）──
   C1 品質ガバナンス(Supabase)   C2 GPTお目付け監査レーン   C3 進捗可視化(/dd)   C4 チーム/Codex運用
```

**読み方の原則（MECE）**
- 軸①＝**静的DB / 動的DB / 横断層**（重なりなし）。
- 軸②＝静的は **7オブジェクト**、動的は **6ソース系統**で割る。
- **著者情報・書誌メタは独立オブジェクトにしない**（③文献・④雑誌のサブとして評価）。
- 1つのDDが複数に跨る場合（#8 論文抽出, #2 学陽 等）は、**跨り先へ「その部分だけ」分解**
  して記載し、複層させない。
- 末尾 §6 の対応表が「全ワークストリームがちょうど1次配置を持つ」検算（漏れ・重複なし）。

---

## 1. 静的データベース ── 7オブジェクト

### ① 法令（statute / e-Gov）
- **定義**: 条文の正本参照。e-Gov 法令へ正規リンク（枝番・漢数字・全角対応）。引用グラフの基点。
- **担当**: 論文抽出の法令リンク部分（`journal-article-legal-linking` #8）、学陽の e-Gov 同期部分
  （`gakuyo-headless-migrate` #2）、KG の法令側（`kg-lit-precedent-rag` #11）。
- **現状（申告）**: e-Gov定義 534（13法令）／学陽 見出し語↔条文 1,731リンク（326見出し語）／
  e-Gov条見出し 4,367条・3,267見出し（7法令）／DB全体 条文参照 mention 10,211。

### ② 判例（precedent / case ＋ 引用グラフ・RAG）
- **定義**: 判例の正本キー（和暦・事件番号・裁判所）と、文献↔判例↔法令の引用グラフ、③RAG。
- **担当**: 知識グラフ（`kg-lit-precedent-rag` #11）、論文抽出の判例リンク部分（#8）。
- **現状（申告）**: case_citations 17,259件（被覆率 40%→100% を地名再抽出で実証）。
  判例の3層着地（内部PD→裁判所HTML→ベンコム）。

### ③ 文献（books / 蔵書 canonical）　← サブ: 書誌メタ・著者・詳細目次(TOC)・横断検索
- **定義**: 蔵書（5,206冊）の正本。書誌メタ・著者(authority)・章節ページ単位の詳細目次を内包。
- **担当**: legallib→biblio 取込（`legal-library-metadata-impact` #4）、詳細TOC×canonical 接合
  （`legallib-integration-design` #5、不変条件＝誤マージ0・人手/NDL目次を劣化させない）、
  横断検索/4図書館ビューワー（`toc-search-rag` #6）、購入レコメンド＝活用（`purchase-…` #7）。
- **現状（申告）**: 蔵書 5,206冊／TOCノード 124k+〜552,544／authority.person 128,081
  （5,647人が複数別名＝名寄せ ground truth）。接合は dryrun→review→apply の段階設計。
- **サブの扱い**: *書誌メタ*=書誌レコード、*著者*=authority 名寄せ、*詳細目次*=bib_toc、
  *横断検索*=活用層。いずれも独立オブジェクトにせず本オブジェクト配下で進捗管理。

### ④ 雑誌（journals / 論文）　← サブ: 論文entity・著者
- **定義**: 法律雑誌の号→論文（{title, authors, 条文/判例参照}）への分解。文献とは別カウントの型。
- **担当**: 論文entity抽出（`journal-article-legal-linking` #8 の article_parser／著者正規化部分）。
- **現状（申告）**: legallib 422号（番頭Mac資産）。parser は実例 fixture で parse_rate 0.9167。
  著者横断検索は authority.person で裏付け。本番スイープは生 `legallib_dl/*.json` 待ち。

### ⑤ 語彙（terms / 法律用語辞書）
- **定義**: 法律用語の見出し語＋定義の正本。JLT・学陽・有斐閣の三点測量で確度担保。
- **担当**: 用語辞書クリーニング基盤（`gakuyo-headless-migrate` #2：JLT v19.0 権威見出し 3,869／
  学陽 all_entries 2,684／三点測量 union 15,654・core 922／読み訂正37件）、
  JLT v19.0 Box着地確認（`box-dispatch-storage` #1：8ファイル byte-exact）。
- **現状（申告）**: 学陽 554件正規化・7,058引用リンク。三点測量済 → canonical 昇格は ratify 待ち。

### ⑥ 手続（procedure）
- **定義**: 法的手続（申立・登記・通知等の手順／要件）の構造化。**現状 専任ワークストリーム未着手**
  （構造placeholder）。⑦書式の slot 抽出（申立・通知・登記系）と接続する見込み。
- **担当**: （未）。**次の一手**: 書式の type別 structure_profile から手続要件を逆算する設計を起票。

### ⑦ 書式（legal templates）
- **定義**: 法律書式テンプレ 3,806件を「文献ではなく再利用する作成物の型」として構造化。
  画像=正本／OCR=検索補助／分類(formType)=入口／構造化=類型別 structure_profile。
- **担当**: 書式テンプレ構造化 tmplstruct（`legal-template-audit-handoff`）。
- **現状（申告）**: 3,806件のうち sample 30件（≒1%）.docx の実構造抽出を検証中。GPT 監査
  `DESIGN_MODIFY_REQUIRED`（outline 中心をやめ type別 slot/span/group へ）。契約839件は月30枠で段階投資。
- **業務効果**: 通れば事務所スキャンPDF書式にも適用可 → Salesforce 組織オブジェクト拡充が容易に。

---

## 2. 動的データベース ── 6ソース系統（取得元で割る）

> 案件（matter）は各系統が解決・収斂する**背骨**。下の系統がそこへ一次データを供給する。

- **Ⓐ Google系** — Gmail（案件ラベル 1,181件を Salesforce ID 付きで構造化）、Google 系資料。
- **Ⓑ Salesforce系** — 案件オブジェクト（sf_id 背骨）。相談→受任の昇格、案件名特定。
- **Ⓒ Box系** — ★LEALA フォルダ（`依頼者_事件名`命名で Gmail と機械照合）、各種成果物。
- **Ⓓ notta（meetings）系** — 打合せ・会議の文字起こし。**現状 未着手**（系統placeholder）。
- **Ⓔ ダイヤルパッド系** — 通話ログ／録音。**現状 未着手**（系統placeholder）。
- **Ⓕ その他** — 上記以外（lawtime 等の時系列 SaaS、郵便物アンカー 等）。

- **担当（横断）**: 案件データ紐付け（`data-linking-progress` #3）が Ⓐ/Ⓑ/Ⓒ を横断結線。
  crosswalk 3システム横断表（sf_id 背骨）、別名候補154・非案件41、GPT CASELINK 監査
  PASS_WITH_NOTES、巻戻し台帳 append-only。**Ⓓ/Ⓔ は今後のコネクタ追加で起票**。

---

## 3. 横断層 ── 仕組み・規律（オブジェクトではない）

- **C1. 品質ガバナンス（Supabase）** — `supabase-data-quality-strategy` #9。clean-only・環境分離
  （staging/prod）・門番二段・「DBを一人歩きさせない（正本はGit）」。全オブジェクトの投入規律。
- **C2. GPT お目付け監査レーン** — `audit-lane-implementation` #10 / `gpt-pro-audit-loop` #12 /
  `gpt-queue-audit` #14 / `queue-audit-ledger` / `gpt-ometsueke-queue-v0.2`。三点照合・台帳・
  **反映キュー**（監査結果≠正本化）・キュー陳腐化検出。全DDの承認動線。
- **C3. 進捗可視化（/dd）** — `pipeline-collect-validation` #15（本ブランチ）。manifest+snapshot から
  runtime_status を描画。合言葉 `/dd`・Mac 日次採取（launchd 9:00）。
- **C4. チーム / Codex 運用** — `codex-setup-docs` #13。`AGENTS.md`・team-scheme・Data DoD・監査の独立性。

---

## 4. オブジェクト間の流れ（依存）

```
[取得・加工]                       [接合・索引]                         [活用]
③文献(書誌/著者/詳細目次) ─┐
④雑誌(論文/著者) ──────────┼─▶ ②判例・引用グラフ ◀── ①法令(e-Gov) ◀── ⑤語彙(用語辞書)
                            └─▶ 横断検索/ビューワー（文献活用）

⑦書式(テンプレ構造化) ──▶ ⑥手続(申立・登記の要件)         （書式→手続は slot 抽出で接続）

動的: ⒶGoogle / ⒷSF / ⒸBox / Ⓓnotta / Ⓔダイヤルパッド / Ⓕその他 ──▶ 案件(matter) 背骨へ収斂

横断: C1 が各段の投入を門番 / C2 が設計を承認 / C3 が現在地を可視化 / C4 が作業規律
```

---

## 5. いま見るべき要点

- **積み上がっている**: ③文献（接合＋横断検索）、①②（法令・判例リンクが本番データで成立）、
  ⑤語彙（三点測量到達）。⑦書式は構造化の検証着手（30件）。
- **承認待ちで律速**: 各オブジェクトの canonical 昇格は **owner ratify ＋ GPT監査(C2)** がゲート。
- **未着手/薄い**: ⑥手続、動的の Ⓓ notta・Ⓔ ダイヤルパッド、雑誌の本番スイープ、A1 biblio ローダ確定。
- 関連DD: `canonicalindex v0.1 DDINDEXDISPO`（GPTキューで未返却検出）＝「索引の扱い」DD。
  本書はその構造面に対応、GPT お目付けの返却を待って整合させる。

---

## 6. ワークストリーム → 一次配置 対応表（MECE 検算）

| ブランチ（PR） | 一次配置 | 跨り（分解先） |
|---|---|---|
| box-dispatch-storage (#1) | 静 ⑤語彙 | — |
| gakuyo-headless-migrate (#2) | 静 ⑤語彙 | ①法令(e-Gov同期) |
| legal-library-metadata-impact (#4) | 静 ③文献（書誌） | — |
| legallib-integration-design (#5) | 静 ③文献（詳細目次） | — |
| toc-search-rag (#6) | 静 ③文献（横断検索） | — |
| purchase-recommendations-topic (#7) | 静 ③文献（活用層） | — |
| journal-article-legal-linking (#8) | 静 ④雑誌（論文・著者） | ①法令・②判例・③文献(著者) |
| kg-lit-precedent-rag (#11) | 静 ②判例・引用グラフ | ①法令 |
| legal-template-audit-handoff | 静 ⑦書式 | ⑥手続(slot→要件) |
| （未起票） | 静 ⑥手続 | — |
| data-linking-progress (#3) | 動 Ⓐ/Ⓑ/Ⓒ（案件背骨） | — |
| （未起票） | 動 Ⓓ notta / Ⓔ ダイヤルパッド | — |
| supabase-data-quality-strategy (#9) | 横 C1 ガバナンス | （全オブジェクトの投入規律） |
| audit-lane-implementation (#10) | 横 C2 監査 | — |
| gpt-pro-audit-loop (#12) | 横 C2 監査 | — |
| gpt-queue-audit (#14) | 横 C2 監査 | — |
| queue-audit-ledger | 横 C2 監査 | — |
| gpt-ometsueke-queue-v0.2 | 横 C2 監査 | — |
| pipeline-collect-validation (#15) | 横 C3 可視化 | — |
| codex-setup-docs (#13) | 横 C4 チーム運用 | — |

→ 全ワークストリームが **静的7オブジェクト / 動的6系統 / 横断4** に漏れなく重複なく配置。
跨りは別列で分解（複層を解消）。⑥手続・Ⓓ/Ⓔ は**定義済みだが未起票**の枠として明示。

---

_v0.2（分類軸 = 浅井先生の正本: 静的7オブジェクト・動的6系統・著者/書誌メタは③④のサブ）。
表示順・サブの粒度・⑥手続と⑦書式の接続は提案。育てる前提。runtime 進捗は `/dd`。_
