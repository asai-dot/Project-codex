# 実民法 real-lane 知見 — ALO データベース設計への参考（2026-06-23）

- 記録: 2026-06-23 / head: Project-codex (claude-code remote) / owner: 浅井
- 経緯: PLAN_lawobject_precision L3（real-lane）＋L4（同定の地盤）を**実 e-Gov 標準 XML の民法で実際に
  コードを動かして**得た、ALO スキーマ（`alo_statutes` / `article_path` 規約 / `alo_edges` / DD-LAWTIME の
  revision キー）に効く経験的事実。数字は実走結果。
- データ: 民法(129AC0000000089) 2 版を GitHub から取得（`japanese_law_xml_schema` テスト=2023-06-14 /
  `gitlaw-jp` current=2025-10-01 施行）。XML 本体はリポジトリに入れない（外部データ）。
- 使ったコード: `scripts/lawdelta`（diff）, `scripts/articlepath`（正準化＋crosswalk）, `scripts/eval`（採点）。

---

## 1. 条番号は文字列順で並べてはいけない（最重要）
- 実民法 **1167 条**の article_path を文字列ソートと数値ソートで比較 → **1156 条で順序が食い違う**。
  例: 文字列順だと `art:10` `art:100` `art:1000` が `art:2` より前に来る。
- **ALO 含意**: 条文の同定・整列・グルーピング・dedup は **数値ソートキー `(main, branch, para, item)`**
  で行う。`article_path` 文字列を `ORDER BY` / 比較に直接使う設計は誤り。`alo_statutes` に正準キーの
  数値分解列（または生成列）を持たせるのが安全。`scripts.articlepath.ArticlePath.sort_key()` がその実装。

## 2. 条番号の 3 表記は 1 つの正準キーに集約できる（実データで 0 件 unparseable）
- e-Gov `Num`=`398_22` / house=`art:398-22` / 漢数字テキスト=`第三百九十八条の二十二` の 3 形を
  `ArticlePath` に正準化 → 実民法 1167 条すべて成功（unparseable 0）。
- **ALO 含意**: `alo_edges`（参照・委任）の join キー、および逐条解説・判決文の**漢数字参照を条文へ
  リンクする橋**は、この単一正準キーで張れる。テキスト側（漢数字）と XML 側（算用）を別 ID で持つと
  接続軸が組めない。**正準 article_path を ALO の条文同定の一次キー**にすること。

## 3. 枝番（第N条の M）の実態：深さ 1・枝番値は大きくなりうる
- 実民法の枝番は **174 条**、`Num` のアンダースコアは**最大 1 個**（の M の K のような二段ネストは民法に無い）。
  ただし枝番値は大きい（**第398条の22**＝抵当権の節）。`398-2` と `398-22` を文字列で比べると誤る（→ §1）。
- **ALO 含意**: branch は文字列でなく整数で持つ。`scripts.articlepath` は**二段ネスト（`398_22_2`）を
  検出したら黙って潰さず ParseError で flag**する設計にした（民法には無いが他法令で出る前に気づける）。
  ＝ALO はモデル化前の形を**沈黙させず例外で可視化**する方針を踏襲。

## 4. 「削除」条は版・取得元で出方が違う（present な空 shell ⇄ absent）
- 同じ民法でも **2023-06-14 版は削除 shell 19 件、gitlaw current は 0 件**。projection や取得器で
  `Article[@Delete="true"]` の残し方が異なる。
- **ALO 含意**: 「条が無い」と「条が削除 shell として在る」を**区別して持つ**。crosswalk/同定は条の
  存在を前提にできない。lawtime の `repealed/deleted` 状態と XML 上の shell 有無を**別事実**として記録する。

## 5. 条より下（項・号）に実体がある：粒度の伸びしろ
- 1167 条の下に **Paragraph 要素 1945 個**（約 1.7 倍）。現 lawdelta は項を条本文に**平坦化**している。
- **ALO 含意**: `article_path` は `:para:/:item:` を表現できる（正準化器も対応）。**項・号粒度で持てば
  分解能が約 1.7 倍**（精度 L5）。`alo_statutes` は条だけでなく項単位の本文・ハッシュを持てる設計が望ましい。

## 6. 編・章・節の階層メタが豊富：グルーピングに使える
- 実民法: **5 編 / 39 章 / 84 節 / 53 款 / 10 目**。現 article_path はこの構造を捨てている。
- **ALO 含意**: 構造上の祖先（編/章/節）を条のメタとして持てば、assembler の dispute グルーピングを
  「裸の条 root」より賢く（章・節単位の文脈）でき、ナビゲーションにも効く。

## 7. 版間の同一性判定そのものが「主張」である（事実として確定しない）
- 実 diff で crosswalk が **`join: art:740 → [art:740, art:774]`** を出した。740（婚姻の届出）と
  774（嫡出否認）は別物の可能性が高く、**複数改正をまたぐ projection 差を 1 回で diff した副作用**
  （誤 counterpart）と見られる。
- **ALO 含意**: 版間の renumber/split/join＝**crosswalk エントリは確度・検証状態付きの assertion**として
  持ち、事実断定しない（DD-SUBTRANS の哲学と同じ）。特に**複数改正をまたぐ diff は単一改正に分けて
  取る**（§8）。crosswalk に `confidence` / `verified` を持たせる。

## 8. revision は (法令, 施行時点 projection, 改正法) で key する必要がある
- 使った 2 版は 2023-06-14 と 2025-10-01施行の **projection 差**で、両者間の diff は**令和4年法律102号
  (親子法制)＋令和5年法律53号(IT化) 等の合算**になった（21 条変化）。
- **ALO/DD-LAWTIME 含意**: 任意 projection 同士の diff は改正を混ぜる。純粋な改正単位の精度を測る/
  edge を張るには、**その改正の施行直前・直後の 2 版**を揃える。revision キーは
  `(law_id, 施行日 projection, 改正法令番号)` で一意化する。

---

## 8.5 改め文が delta_kind の公式真実源（text-diff は代替）
- 「どの条をどう変えたか」は**改正法の「改め文」が公式に断定**（「第七百三十三条を削る」「第七百七十二条を
  次のように改める」「…の次に次の一条を加える」）。＝delta_kind は推定でなく**官報の一次データから確定**できる。
- 本セッションの lawdelta は 2 つの溶け込み済み版を text-diff して 21 条を推定したが、これは**改め文が
  取れない場合の代替**にすぎない。改め文が取れるなら、それが gold かつ第一次抽出になる。
- **ALO 含意**: `alo_edges`/改正レーンに**改め文パースの第一級レーン**（名大16パターン / e-Gov v2 改正履歴）を
  置く。text-diff(lawdelta) は「溶け込み済みしか無い古い改正」等の補完。gold は改め文/新旧対照表から
  **機械生成**（人手目視ではない）。e-Gov allowlist が前提（本環境は 403）。

## 9. 直接の次アクション（このセッションで作った土台の上で）
1. **gold は公式データから機械生成**（人手目視ではない）: 改正法の「改め文」（e-Gov 法令API v2 改正履歴 /
   名大16パターンで解析）または公式新旧対照表から 21 条の `delta_kind` を自動付与 → `scripts.eval --min-f1`
   で lawdelta 閾値較正（L1）。改め文が操作を断定する以上、人手ラベリングは不要。
   ＊本サンドボックスは e-Gov allowlist 外(403)・gitlaw に該当改正法（令和4年102号/令和5年53号）未収録のため
   未取得＝**環境/アクセスの問題**。要 e-Gov allowlist もしくは改正法を含むミラー。
2. **crosswalk に confidence/verified 列**（§7）を足し、§8 に従い単一改正の 2 版に絞って誤 join を消す。
3. `alo_statutes` 設計に §1（数値キー）・§4（削除 shell）・§5（項粒度）・§6（階層メタ）を反映。
4. 接続軸（DD-LAWREF-001）の参照 edge は **正準 article_path（§2）を join キー**に Lawtext 出力を写像。

## 10. 不確実な点
- 21 条の delta_kind は **producer 予測**で未検証（gold 化は asai の新旧対照表照合待ち）。
- `join: 740→774` は誤 counterpart の可能性が高いが、断定はしない（要検証）。
- 枝番二段ネストは民法に無く未モデル化（出たら ParseError で flag）。他法令での実頻度は未調査。
- 取得 2 版の projection 仕様（gitlaw の `revision_id=20251001_…` の正確な意味）は gitlaw 実装準拠で、
  e-Gov 公式の時点定義との完全一致は未確認。
