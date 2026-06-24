# cc_order: JLT v19.0 golden data — byte-exact ingest to Box canonical

- order_id: cc_order_jlt_v19_box_transport_20260601
- issued_by: claude.ai (head agent)
- issued_at: 2026-06-01 JST
- status: candidate (浅井さん職権 accept 前提。location は accept 済み = A)
- supersedes: return handoff の再 dispatch 先 `docs/alo/external_canonical/jlt_v19.0/`
  （却下理由は §1）
- source session: JLT v19.0 取得・検証・acquisition_log 作成（hand agent: claude-code-windows 想定）

---

## 0. 決定サマリ

1. MCP 経路は使用不可で確定（§2 検証）。binary 転送・フォルダ作成とも hand agent の
   Box API 直叩き（boxsdk 等）に寄せる。
2. golden data の canonical 着地先は **05＿語彙レイヤー（folder_id 370003701279）配下に
   新規フォルダ `jlt_v19_0` を切り、8点 + acquisition_log を束ねる**。docs/alo（設計ドキュメント木）
   には置かない。
3. 8点は text/binary で分割せず byte-exact の単一経路で転送する（§1）。
4. 取得時 SHA-256 → landing 後の往復 hash 一致まで取って初めて「格納完了」とする（§3）。

---

## 1. 設計判断（なぜこの形か）

### 1-1. text/binary 分割の禁止
取得8点: 辞書XML / CSV(UTF-8) / CSV(SJIS) / PDF / Law DTD / Dict DTD / dtdページHTML snapshot。
このうち **CSV(SJIS) を text 文字列として転送すると UTF-8 再エンコードで確実に破損する**
（Shift-JIS 仕様上の帰結）。これは 5/25 発覚の nightly Box backup / ChatworkHarvest の
cp932 破損（約33日サイレント失敗）と同一の事故クラス。よって text/binary で割らず、
**全8点を raw bytes の単一経路で転送**する。SJIS の golden 性（SJIS バイト列であること自体が価値）
を殺さない。

### 1-2. 着地先 = 語彙レイヤー（docs/alo ではない）
JLT は法律用語辞書 = 語彙レイヤーの golden source。05＿語彙レイヤー（370003701279）には
既に前版 `dict_v18_xml.xml`（約1.06MB）が直置きされている。v19 は同一 golden 資産の版更新。
docs/alo は .md 設計書の木であり、ここに DATA を混ぜると三層 SoT 分裂（紙設計／DD-PGDB-001／
Supabase）に第4断片を足す。

### 1-3. 版フォルダ規約を v19 から導入
v18 はフォルダ無し直置き。v19 は8点セット + manifest を束ねるため版フォルダ `jlt_v19_0` を切る。
**v18（dict_v18_xml.xml）は touch しない**（既存 canonical を理由なく動かさない）。
v18 のフォルダ正規化（jlt_v18_0/ への収容）は別 DD で後日判断、本 order の scope 外。

---

## 2. 検証済み事実（推測でない）

- 接続中 Box MCP に `get_upload_url` がツール露出していない。`upload_file` は text-only / 5MB 上限。
  → binary 不可。
- 05＿語彙レイヤー（370003701279）は external に共有されたツリー。MCP の create_folder が
  external-access guard で拒否（req_011CbcXn9dHigPb5QowB1ZpY）。upload_file_version も従来から
  write guard 対象。→ この正典ツリーに対し MCP は text-only かつ書込ガードで二重に使用不可。
- handoff の再 dispatch 先 docs/alo/external_canonical/jlt_v19.0/ は docs/alo 直下に未存在
  （要新規作成と一致）。本 order で却下し §1-2 の着地先に差し替え。

備考（governance 向け・本 order scope 外）: 語彙レイヤーが外部共有である点は監査対象。
JLT は法務省の公開データのため機密性の問題は無いが、外部共有ツリーへの canonical 格納という
事実は記録しておく。

---

## 3. 実行手順（hand agent）

### Step 0 — 環境申告（head へ返す。これ無しに転送を撃たない）
- 0-1: scrape機（H:\work\jlt_v19_dl\ がある機）の Box 書込手段の有無
  - Box API 資格情報（boxsdk JWT app / developer token）が同機に在るか
  - Box Drive が導入されているか / 同期対象フォルダは何か
- 0-2: 取得8点の取得時 SHA-256。acquisition_log に未記録なら今算出して追記
- 0-3: 各ファイルの実バイトサイズ（PDF・XML が想定内か確認用）

### Step 1 — 経路選択（Step 0 の結果で分岐）
- (推奨) 資格情報あり → boxsdk で
  1) 親 370003701279 配下に `jlt_v19_0` フォルダ作成、生成 folder_id を取得
  2) 8点を chunked / multipart で byte-exact upload（SJIS は raw bytes、再エンコード禁止）
  3) スクリプトは再利用可能に保存（次の外部 golden = JLT v20 / 他辞書で再利用）
- Box Drive のみ → 同期フォルダ内に `jlt_v19_0` を作り 8点を cp（byte-exact）、同期完了を待つ
- どちらも無 → 浅井さん手動（Box web UI）へエスカレーション。byte-exact だが自動化なし

### Step 2 — landing 後の往復検証（全経路共通・必須）
- Box から 8点を再 DL し SHA-256 を再計算 → Step 0-2 の取得時 hash と全件一致を確認
- 一致しないファイルが1点でもあれば格納失敗扱い。再転送
- 一致を acquisition_log に記録（file名 / 取得時hash / landing後hash / 一致 / Box file_id）

### Step 3 — 完了報告（return handoff）
- 生成された `jlt_v19_0` の folder_id と 8点の Box file_id 一覧
- 往復 hash 一致結果
- standup へ1行 append（amendment パターン）

---

## 4. scope 外（混同しないこと）

- XML 内蔵 DTD(v3.0) と単体 Dict DTD(v1.0) の系統差 → ingest 設計（term_dict）の論点。
  transport では触らない。hand agent の parking は正しい。
- term_dict ingest 設計の解禁 → 本 order 完了（往復検証 PASS）後。それまで gate。

---

## 5. 完了条件（DoD）

- [ ] 05＿語彙レイヤー/jlt_v19_0/ に 8点 + acquisition_log が landing
- [ ] 取得時 hash = landing後 hash が 8点全件一致、acquisition_log に記録
- [ ] jlt_v19_0 folder_id と 8 file_id が return handoff に明記（幽霊参照ゼロ）
- [ ] v18（dict_v18_xml.xml）は不変更
