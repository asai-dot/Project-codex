# ⑥手続 設計メモ — どこから手をつけるか（v0.1 提案）

> **思想層は `docs/dd_doctrine.md`（設計思想ドクトリン）**。本書はその具現化＝着手の実装メモ。
> 「なぜこうするか」（作動法＝制定法∪実務補充／典拠の梯子／名著蘇生／真偽でなく足場 等）は
> ドクトリンを読むこと。本書は「どこから手をつけるか」の how。

> ⑥手続は「統合軸（横串）」（→ `docs/dd_index.md` §1-⑥）。**単一のデータセットが無い**ため
> 着手点が見えにくい。本書は「巨大オントロジーを作らず、最小の背骨を1本通して既存データを
> 後から繋ぐ」方針で、**最初の一歩**を具体化する。中身（類型・名称・根拠法令）は浅井先生の
> 補正前提のドラフト。

> ## ⚠ 重要な層の区別（v0.2 訂正）
> **書式/書名を手続類型へ突合する `procedure_match` は「層0＝入口の分類（どの手続"群"の話か）」
> にすぎない。手続そのものではない。** 手続は **分岐するプロセス（フローチャート/DAG）**——
> 条件分岐・並行・期限・サブ手続参照を持つ——であり、一軸のラベルや時系列の一列では捉えられない
> （例: 破産＝申立→開始決定→{同時廃止｜管財}→…、免責は並行）。
> **層0(分類) ≠ 手続モデル層**。後者（§8）が本丸。分類は「入口で荷物を仕分ける」だけ、
> 中の分岐の構造化が手続の核心。本書 §1〜§7 は層0の立ち上げ、§8 が本丸の設計。

## 1. なぜ難しいか（問題の構造）

- 手続は ①法令(根拠)・③文献(解説書)・⑦書式(申立書等)・②判例(争点) が**手続類型をキーに収斂**
  する横串。元になる「手続マスタ」がどこにも無い。
- だからトップダウンに完全な手続オントロジーを書こうとすると終わらない。
- **筋**: まず**有限で権威的な背骨**を1本引き、**既に動いているデータ**から面を1枚ずつ張って育てる。

## 2. 出発点（ウェッジ）＝ 手続類型 spine を「根拠法令」から引く

- **法令→手続はほぼ 1:1 で有限・権威的**（民訴法→訴訟／民保法→保全／民執法→執行／破産法→倒産…）。
  事務所の現業ならコア類型は **20〜30 個**で足り、先生が短時間で列挙・補正できる。
- これを `pipeline/procedure_spine.json`（同梱 v0.1 ドラフト）に**正本化**。以後すべての join キー。
- spine の各エントリ = `{id, 系統(民事/刑事…), 名称, 根拠法令, aliases}`。aliases は書式/書名との突合用。

## 3. 最初に張る面 ＝ ⑦書式（タイトル × spine alias 突合）

**理由（ここが一番おいしい）**: tmplstruct（⑦書式）は**いま動いていて** 3,806 書式を扱っている。
書式が在る＝**その手続を実務で現にやっている**裏取りになる（机上でなくデータで手続の実在を確認）。

**重要な発見（archetype ≠ 手続類型）**:
- tmplstruct の分類は **archetype A〜E**（A契約/定款656・B申立478・C登記届出145・D通知催告1291・E記入フォーム1236）。
  これは「**再復元の構造型**」であって手続類型ではない（doc 明言「formType/category は型に乗るラベル」）。
- **契約系(A)は"取引文書"で手続ではない** → 書式→手続の wedge は **B申立 / C登記 / D一部** に効き、A契約は対象外。
- 手続シグナルは archetype でなく **書式のタイトル/件名**にある（「破産手続開始申立書」「仮差押命令申立書」）。
  これは **spine の `aliases` と部分一致で突合できる**。

**実装（runnable）**: `scripts/procedure_match.py`（stdlib）。書式リスト(jsonl/csv の `{id,title}`)を読み、
spine の name/alias をタイトルへ突合して `procedure_id` を付与＋「**手続類型 × 書式件数**」を集計。
契約等は alias に当たらず unmatched（＝「契約は手続でない」が自然に出る）。曖昧一致は隠さず candidates に列挙。

## 4. 次に張る面（コスト順）

1. **①法令(根拠)** — spine に既に紐付く（背骨そのもの）。e-Gov 法令 ID を当てるだけ（`gakuyo_law_index` 流用）。
2. **③文献** — **同じ `procedure_match.py` を蔵書タイトルに適用**（`--label 文献 --list`）。実務書の存在で
   手続を裏取り＋「この手続を調べるならこの本」導線。書名は2段で突合する:
   - **leaf**: 手続名/alias を含む実務書（「民事保全の実務」→民事保全）。
   - **broad**: 手続名は無いが**根拠法令が手続法**の広い本（「家事事件手続法の解説」→家事）。
     実体法書（「民法総則」「注釈会社法」）は手続でないので**未一致のまま**（誤検出回避）。
   - 既知の穴: 「刑事弁護の手引」のような系統名だけの本はリーフにも手続法名にも当たらず未一致。
     系統(刑事/民事)レベルの突合が要るなら spine に系統 alias を足す（過剰一致に注意）。
3. **②判例** — 手続上の争点の裁判例。`case_citations`(②) に手続タグ。最後でよい。
4. **動的: 案件(matter)** — Salesforce の事件種別/Box フォルダ → 手続類型。**実務頻度の分布**が出る
   （どの手続が多いか＝投資優先度。⑦書式の月30枠の順番付けにも効く）。

## 5. 最小スキーマ（join 層）

```
procedure_type(spine)
  ├─ 法令 face : 根拠法令(e-Gov law id)            ← spine に内包
  ├─ 書式 face : formType_to_procedure.csv で join  ← まず作る
  ├─ 文献 face : 書名/NDC/主題 → procedure_id        ← 次
  └─ 判例 face : case_citations.procedure_tag        ← 後
```
- 各 face は **spine とは別の対応表(crosswalk)**で張る（spine 本体は太らせない）。
- 「全貌が見える」＝ `procedure_id` で 4 face を引けば 根拠法令・実務書・申立書式・裁判例が一括で出る。

## 6. v0.1 の具体的な第一歩（今週やること）

1. **先生**: `pipeline/procedure_spine.json` をレビュー/補正（類型の過不足・名称・根拠法令・行政の扱い）。
   → これが確定すれば背骨が立つ。**v0.1=24類型は方向 OK の確認済**。
2. **ワーカー(Mac)**: tmplstruct の書式リスト（`{id,title}` の jsonl か csv）を書き出す。
3. **番頭**: `python scripts/procedure_match.py --templates <書式リスト>` を実行
   → 「**手続類型 × 書式件数**」が出る。ここで ⑥手続が初点灯（地図に実体が宿る）。
4. 未一致(契約等)・曖昧一致を見て、spine の alias を補強（タイトル語彙に寄せる）→ 再実行で精度を上げる。

> いきなり完璧を目指さない。spine 20〜30 行 ＋ formType 対応表 1 枚で「動く最小の手続ビュー」を
> 出し、案件頻度（§4-4）で重要な手続から面を厚くする。

## 7. ダッシュボードへの将来接続

- 当面 ⑥手続は**構造表示（地図）**のまま（`/dd` の structure セクション）。
- spine が立ったら「**4 face のカバレッジ**（各 procedure に法令/書式/文献/判例が何件張れたか）」を
  probe 化して roll-up（例: `procedure_spine.json` を読み crosswalk の充足率を出す count 系 probe）。
- 動的との接続: 実案件が procedure_id を持てば、案件画面から「根拠法令・実務書・書式・裁判例」へ即ジャンプ。

## 8. 手続フローモデル層（本丸）

§1〜§7（spine＋分類）は**入口**にすぎない。手続の核心は「**分岐するプロセス**」の構造。
だが——**事務所ポリシー＝巨人の肩に乗る。手続フローはゼロから手作りしない。** owner が
知らない分野を手で描けばミスが出る。手続の構造は**既に権威ある資産に入っている**ので、
それを**抽出・突合**し、owner/GPT は**監査**するだけ（語彙の三点測量・GPT監査レーンと同じ流儀）。

- **手続＝有向グラフ**: 局面(node)＋条件付き遷移(edge)＋時系列/期限。線形でも単一ラベルでもない。
  並行サブ手続・別手続参照・差戻し(ループ)を持つ。
  - 例(破産): 申立→開始決定→**{同時廃止｜管財}**→(管財)債権届出→調査→配当→終結。免責は**並行**。
  - 例(民事保全): 申立→**{審尋｜無審尋}**→発令→執行→**{保全異議／取消／即時抗告}**→本案へ接続。

- **フローの出所（手作りせず、既存資産から抽出）**:
  1. **手続法の条文構造（①法令/e-Gov）＝法定の順序・分岐の根拠**。章・節・条見出しが手続の骨格。
     → **既に保有**: 民事訴訟法(条見出し446)・刑事訴訟法 ＋ e-Gov law_id（民訴 `408AC0000000109` /
     刑訴 `323AC0000000131`、`gakuyo_law_index.json`）。未取得(破産法/民保法/民執法/家事手続法)は
     e-Gov 取得対象に足すだけ（取得経路は①で既存）。
  2. **実務書・コンメンタールの詳細TOC（③文献, 既に124k+ノード保有）＝流れの章立て**。
     「破産法コンメンタール」「民事保全の実務」の目次は手続ステップに沿う。同手続に重ねて肉付け。
  3. **裁判所HP の手続案内＝公式フロー図**（②判例の3層着地と同じ harvest 路線で取得可）。

- **詳細TOC源の実査（重要）**: 書誌は2源 — **bencom-library（弁護士ドットコムライブラリー）3,802冊**は
  **綺麗な詳細TOCを Supabase `biblio.bib_toc` に保有（OCR不要）**、**asai-bookshelf（自炊）6,524冊**は
  OCRノイズ大。`会社法実務スケジュール`（新日本法規）は **bencom 外＝自炊のみ**（OCR荒い）。リーガル
  ライブラリーは当DB未取込。→ **パイロットは bencom 収録の手続本（clean TOC）を優先**。
  例: 「商業登記全書／7 組織再編の手続〈第3版〉」は**株式交付の11ステップをページ付きで保有** →
  `pipeline/procedure_flow/commercial_share_delivery.json`（`status: extracted_toc`）に実フロー化済。

- **組み立て**: 手続法の章節条(骨格) ＋ 実務書TOC(肉) ＋ 裁判所HP(公式) を `procedure_id` で突合して
  flow を**生成**。法的確度は**複数権威資産の一致**(条文×実務書×裁判所HP)で担保＝**三点測量流**。

- **スキーマ案** `pipeline/procedure_flow/<procedure_id>.json`（各 node に出典 `source` を必須化）:
  ```
  { "procedure_id": "...", "source": ["egov:lawId", "book:isbn#章", "court:url"],
    "nodes": [ { "id":"...", "局面":"...", "根拠条文":["egov:lawId#art"], "期限":"...",
                 "書式":[...], "判例":[...], "実務書":["isbn#章"],
                 "次":[{"to":"...","条件":"..."}], "サブ手続":[...] } ], "entry":"...", "terminal":[...] }
  ```
- **4 face は手続全体でなく "各 node" に張る**。全貌＝ある局面に立つと その 根拠条文・必要書式・
  典型判例・実務書の該当章 が出る（§5 の procedure 単位は粗い近似、本来は node 単位）。

- **役割分担（訂正）**: **owner は手続を作らない・監査する。** 抽出(条文構造/TOC/裁判所HP)・突合・
  フロー図描画は番頭/機械。owner と GPT は「順序・分岐が権威資産と一致しているか」を確認するだけ。

- **実装（済）**: `scripts/procedure_flow.py`（load/validate/render、stdlib）＝手続フローを**保持・
  検証・分岐つきフロー図描画**できる。各 node の `source`(出典) 必須で捏造を弾く。保管は
  `pipeline/procedure_flow/<id>.json`（→ `_README.md`）。雛形 `commercial_share_issue.example.json`
  で公開/非公開会社の**分岐が構造として保持できる**ことを実証（`status: scaffold_pre_audit`）。
- **着手（推奨ソース）**: 段取り本 **「会社法実務スケジュール」**（分岐つき業務段取りの良書）を起点に、
  その業務スケジュール（分岐・期限・必要書類・根拠条文）を抽出 → flow JSON 化（source にページ）。
  条文(①/e-Gov・会社法は保有)・実務書TOC(③)・裁判所HP と突合（三点測量）→ owner/GPT 監査。
  別ルート: 既に条見出しを持つ 民訴/刑訴 を条文構造から skeleton 抽出。いずれも**手作り不要**。
- **STEP 1（実装済・橋渡し）**: `scripts/procedure_flow_from_toc.py` ＝ 本の**詳細TOC**を読み、章=業務・
  節=順序付き局面 として **flow 雛形(`status: toc_stub`)を自動生成**（各 node に「書名 p頁」出典）。
  TOC は順序を持つが分岐は持たないので生成物は線形 stub。分岐・根拠条文・期限・書類は本文＋条文から
  後付け＋監査。ワーカー発注書: `pipeline/procedure_flow/WORKER_TASK_kaishaho_jitsumu_schedule.md`
  （会社法実務スケジュールの ISBN 特定・PDF/詳細TOC 確認・TOC を jsonl 出力）。

---

## 9. spine の bottom-up 裏付け（実データ照合・止揚の実証）

「spine は上から作るな、本の業務一覧から立ち上げろ」を**実データで検算**した。bencom 手続本の章構造
（Supabase `biblio.bib_toc`）から経験的インベントリ `pipeline/procedure_inventory.json` を作り、
`scripts/spine_reconcile.py` で a-priori spine(24類型) と照合：

- **過少解像（最大の発見）**：spine「商事・会社非訟」**1類型に、実データでは6手続**
  （合併／会社分割／株式交換／株式移転／組織変更／株式交付）がぶら下がる ＝ **要分割**。
- **欠落**：spine は特別清算のみ。**通常清算**が無い。
- **欠けた軸**：清算は**法人類型別**（株式会社/医療/社福/NPO/宗教/学校/持分会社/士業）で枝分かれ。
  spine に entity-type 軸が無い。
- **粒度の caveat**：level-1 章 ＝ 手続 とは限らない。組織再編＝章は手続群、略式手続＝章は局面(steps)。
  **経験的手続単位は TOC level に固定できない**（`kind` で明示し owner 監査）。

→ **結論（GPT お目付け 20260619 DDPROGRESS `PASS_WITH_NOTES` で校正済）**: 初回サンプル（数冊）で
**商事系の過少解像と欠落・法人類型 facet の必要性が確認**された（※「24類型全体が粗すぎる」とまでは未実証）。
向きは **bottom-up GO**。ただし二者択一にせず**三層**で持つ：

| 層 | 中身 | 正本性 |
|---|---|---|
| **L0 observation** | TOC/法令/公式案内由来の生観測（`procedure_inventory.json`, kind付） | 観測のみ・正本でない |
| **L1 registry** | 操作的定義を満たし **owner ratify** された procedure / family / variant（安定ID） | 正準レジストリ |
| **L2 roll-up / facet** | 旧24類型(navigation)・系統・法人類型・forum 等のビュー | 唯一の真理にしない |

- **商事6手続**は `commercial_nonlitigation`（裁判所の会社非訟）の下で「分割」ではなく、会社法手続の
  **`corporate_reorganization` family を新設して再分類**（category error 回避）。会社非訟＝検査役選任等は別維持。
- **法人類型**は直積表にせず**疎な applicability crosswalk / `procedure_variant`** で持つ。
- `kind` の操作的定義: `procedure`(目的･契機･根拠･局面列･終局を持つ過程) / `procedure_family`(束ね) /
  `procedure_variant`(主体･法人類型差で局面分岐) / `flow_step`(局面・単独でID鋳造しない) / `dimension`(facet)。
- **HOLD**: spine 正本置換・DDL・DB write・`requirement_floor` accepted化・MCP publication。e-Gov 各号の
  **read-only 取得は並行 GO**。商事再分類・三層化・entity facet は **owner ratify packet** に出す（自動正本化しない）。
- 監査記録: `docs/dd/20260619_spinebottomup_v0.1_DDPROGRESS_{REQUEST,RESULT}.md`。
- 本ツール `spine_reconcile.py` は観測を **kind 別に集計**し、過少解像/未マップ手続/未観測類型(`not_observed_in_current_sample`)/
  source coverage(冊数・系統) を機械出力する（サンプル依存を可視化）。

### §10 記載事項の床の top-down 源 ＝ e-Gov 各号（read-only / 並行 GO）

§5（記載事項の床）の **top-down 正準リスト＝条文各号** を、e-Gov 法令データから機械取得する
`scripts/egov_fetch.py` を追加（stdlib のみ・GET のみ）。各号を **law/article/item anchor**
（`{law}/a{条}/p{項}/i{号}`）として取り出し、`requirement_floor.py --canonical` が consume できる
形（id/名称/号/aliases）で raw 保存する。巨人の肩: 各号の区切り（法令構造）は e-Gov 正本を
**consume**、我々は anchor 正規化と床ツールへの受け渡しだけを担う。

**境界（GPT RESULT §5/§4 の HOLD を厳守。コードの不変条件としてテスト固定）**:
- 出力は全件 `layer=L0_observation` / `status=observed`。**procedure へ紐付けない**
  （`procedure_id`/`spine_ref` を持たせない）。
- **floor accepted化しない**：床への昇格は requirement_floor の N書式収束 + owner ratify を経る別工程。
- **DB write しない**：raw 保存はファイルのみ。canonical mapping・MCP publication は HOLD。
- offline parse パス（`--from-file`）と fixture（`tests/fixtures/egov_kaishaho_199.xml`）で
  ネット非依存に検算（`tests/test_egov_fetch.py`）。**live 取得は outbound 許可の実行環境で**
  （`--law-id` ＋ `--raw-dir`、または `--targets pipeline/egov_raw/_targets.json` で一括）走らせ、
  raw を持ち帰る（`pipeline/egov_raw/README.md`）。

**後続＝床突合（`scripts/floor_reconcile.py`・実装済）**: 各号 anchor（top-down）× N書式（bottom-up）を
`requirement_floor` で突合し、法定の床／実務必須／**alias 要整備**（条文本文＝長文 anchor が書式の短語と
未マッチで被覆0 ＝ curation の的）を出す。anchors の JSON は `{items:[{id,名称,号,aliases}]}` で
`requirement_floor` がそのまま consume できる。**raw が落ちれば即通る**状態（fixture→anchors→床突合の
端から端まで `tests/test_floor_reconcile.py` で固定）。⇒ owner が許可環境で fetch→raw コミットすれば、
床突合は番頭が担当。

### 残タスク（owner ratify packet 待ち・自動正本化しない）

| # | タスク | 状態 | 根拠 |
|---|---|---|---|
| T1 | **商事系の再分類**：組織再編6手続を `commercial_nonlitigation` 直下に置かず `corporate_reorganization` family 新設へ。会社非訟（検査役選任等）は別維持 | **owner packet 起票済（`20260621_commercialreclass_v0.1_DDPROCREG_REQUEST`・queued/未投函）** | RESULT must_fix5 / §2-2 |
| T2 | 法人類型 facet を疎な applicability crosswalk / `procedure_variant` で設計 | parked | RESULT Q3 |
| T3 | L1 procedure_registry（owner-ratified・安定ID・supersession map）の起票 | **scaffolded（器+ゲート実装・owner_ratified 0件）** | RESULT Q1 / must_fix6 |
| T4 | inventory を独立2source（or 法令/公式1 + 実務書1）へ拡張、candidate 昇格条件の定義 | **昇格条件は実装済（拡張は parked）** | RESULT should_fix3 |

> T1 は今回 owner の指示で**タスクとして保留**（今 session では着手しない）。e-Gov 各号取得（§10）を先行。

### §11 L1 procedure_registry の器とゲート（三層化の真ん中）

`pipeline/procedure_registry.json`（**owner_ratified 0件で起票**）＋ `scripts/procedure_registry.py`。
観測(L0)→registry(L1)→roll-up(L2) の真ん中を実装。番頭の権限は**ゲート検算と候補提示のみ**：

- **promotion_report**: 昇格ルール（独立2 source_family、または 法令/公式1 + 実務書1）で candidate 候補を
  **提示するだけ**。実 inventory は単一source中心 ＝ **0/8 が昇格適格**（must_fix7「1冊1章 auto-accept
  しない」がそのまま発火）。independent source が増えるか owner ratify で初めて上がる。
- **validate_registry**: status lifecycle（observed→candidate→owner_ratified→superseded/deprecated）、
  **owner_ratified は ratified_by/ratified_at 必須**（自動鋳造を禁止＝コードの不変条件）、
  supersession グラフ（dangling/循環）、legacy_rollup_id の L2 整合 を検査。
- **crosswalk**: L1 entry → L2 roll-up の被覆レポート。

HOLD 厳守: owner_ratified への昇格は **owner の手**（ratify メタ追記）でのみ。番頭は spine 正本も
registry の owner_ratified も自動で書かない。テスト `tests/test_procedure_registry.py`（20 checks）で固定。

---

_v0.3（巨人の肩に乗る）。手続フローは**手作りしない**。出所＝手続法の条文構造(①/e-Gov・民訴刑訴は保有)
＋実務書/コンメンタールのTOC(③・保有)＋裁判所HP。突合して生成し、owner/GPT は監査(三点測量流)。
layer0=分類(procedure_match)は入口、本丸=node 単位フロー(§8)。spine=`pipeline/procedure_spine.json`、
bottom-up 裏付け=`procedure_inventory.json`＋`spine_reconcile.py`(§9)。_
