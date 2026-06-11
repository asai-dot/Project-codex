# DD-FORMOBJ-001 v1.0: 書式オブジェクト — 設計文書（2026-06-11 議論の集約）

> **id**: DD-FORMOBJ-001 / **version**: v1.0-draft / **supersedes**: v0.1-draft（S0-S3骨格は §6 に吸収）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / date: 2026-06-11
> **gate**: 設計のみ。DDL・DB書込みなし。
> **位置づけ**: 本日のスレ（所蔵突合→自炊監査→ポイントOCR→toc_nodes→S0-S3→L3 PoC→解説接地への転換）の決定事項を、書式オブジェクトの v1 設計として固定する。

---

## 0. owner テーゼ（本DDの根本前提）

1. **書式だけからの構造化は悪手**。答えのないブラインドテストになる（抽出者=判定者）。
2. 書式は「結論」である。**何を載せるべきか／載せると何が起きるか／なぜその構造か**は書式自体に書かれておらず、**解説書・法令・契約類型論・条項例の解説・書式の書き方**という「理由を語るテキスト」に書いてある。そこが answer key。
3. 契約条項の実務の知恵とは、**条項の原則的なあり方**と、それを**どう緩めるか・どう締めるか**（押し引き）である。
   - 緩んでいるのか締まっているのかは、**観測（書式の読み比べ）だけでは判定できない**。
   - 緩める/締めるが**どちらの当事者に有利/不利か**という関係性は、**より大きなコンテキスト**（解説・法令・契約類型）から読んでこなければならない。
4. 大量に読み比べて差分を出すだけなら世のLLMが既にやっている。**法律家の書式議論はそれでは成立しない**。
5. ゆえに **複数の解説書への接地が必須**であり、**文献OCRの進捗が本プロジェクトの律速**である。

## 1. フェーズモデル（ゴールの段階定義）

| Phase | 内容 | 状態 (2026-06-11) |
|---|---|---|
| **P1 転写** | 目で見た書式を文字どおり起こす（restorable）。人間でも打てる＝価値の本体ではないが、材料として必要 | **できる**。自炊600dpi×vision OCRで実証（解除通知/製造委託/発起人決定書）。restorable_profile v0.3.1 が既存設計 |
| **P2 構造体把握** | 何が書いてあるかの構造（条項区切り・意味型slot・義務/権利・archetype） | **動く**。L3 PoCで4タイプ（契約/定款/議事録/通知）の自動抽出と横断クエリを実証。ただし**タグは自己採点＝検証不能**が限界 |
| **P3 意味構造** | 条項が**本来の意味的構造**を持つ：原則形・押し引きの選択肢・有利不利の方向・法令根拠に**接地**した設計知識 | **未到達＝本来のゴール**。再委託1件で接地抽出の型を実証（`poc_grounded/`）。**だいぶ先**。律速は文献OCR |

> P1/P2 は P3 の材料調達である。P2 の構造体は P3 の設計知識から「答え合わせ」されて初めて検証可能になる。

## 2. オブジェクトモデル（二層）

### 2.1 form_object（P1/P2層）— 個々の書式
v0.1-draft の S0-S3 設計を維持（住所先行・snapshot/canonical分離・発明禁止・sticky form_uid）:
```text
form_object
  form_uid / anchor(canonical_book_id + toc_node_id + page_span) / form_title / form_kind
  content(blocks: heading|party|recital|clause|item|signature|date|attachment|note, blanks, …)
  provenance(源別snapshot) / canonical_source / quality / confidence(分解)
  + P2拡張: clause.function(暫定タグ) / 意味型slots / obligations|rights
  + P3リンク: clause.design_knowledge_ref → clause_design_knowledge   ★v1.0新設
```
P2のfunctionタグは**暫定**（lowercase推測）であり、P3の設計知識にリンクされたとき正準化される。

### 2.2 clause_design_knowledge（P3層）— 条項機能の設計知識 ★本DDの中心
**単位 = 条項機能**（再委託・損害賠償・知財帰属・支払…）。書式でなく**解説/法令から**抽出する。
```jsonc
clause_design_knowledge {
  clause_function,            // 例: subcontracting
  baseline,                   // ★条項の原則的なあり方（例: 再委託は原則禁止+事前承諾で限定許容）
  rationale_why,              // なぜその原則か（当事者構造・リスク配分の理由）
  must_address: [],           // この機能の条項が載せるべき論点
  design_options: [{          // ★押し引きモデル
    axis,                     // 何の押し引きか（例: 再委託先の行為への責任）
    choices: [{
      choice,                 // 具体的な書き方
      effect,                 // 載せると何が起きるか
      favors,                 // ★どちらに有利か（委託者/受託者/中立）= 緩め/締めの方向
      tightness,              // tighten | loosen | neutral（原則形に対して）
      legal_caveat            // 法令上の注意（例: 旧民法105条削除で限定説の根拠弱化）
    }]
  }],
  legal_basis: [],            // 法令・改正・一問一答・判例
  grounded_from: [{           // ★引用必須（接地の証跡。これがanswer key）
    source, printed_pages, pdf_pages, toc_anchor, extracted_by
  }],
  source_diversity,           // ★単一書か複数書か（n_books）。複数解説書の合成が目標
  form_instances: []          // この知識のインスタンスである書式（form_uid/条項例）へのリンク
}
```
**検証原則**: タグの正しさは「私がそう思う」でなく**引用追跡**で検証する（grounded_from の解説テキストに根ざすか）。ブラインド脱却の仕組みそのもの。

## 3. 押し引きモデル（P3の核）

- 各条項機能に **baseline（原則形）** がある。実務の知恵は baseline からの **tighten/loosen** とその **favors（有利不利の方向）**。
- **観測（書式読み比べ）では tightness も favors も判定できない**。解説・法令という大きなコンテキストからのみ取れる。
- 実証済みの一例（再委託, `poc_grounded/saiitaku.knowledge.json`）:
  - baseline: 原則禁止＋事前承諾で限定許容（理由: 当事者は委託者・受託者のみ、再委託は受託者の責任）
  - 押し引き: 責任を「選定・監督のみ」に限定 → **loosen / favors=受託者** ／ 全責任 → **tighten / favors=委託者**
  - 法令根拠: 旧民法105条1項の削除 → 限定説の根拠弱化（解説の脚注から取得）

## 4. 依存関係と律速（正直な見積り）

```
P3 設計知識 ←接地← 複数の解説書テキスト ←─ 文献OCR（自炊600dpi＋ポイントOCR）★律速
                 ←接地← 法令（e-Gov）・一問一答・判例
P2 構造体   ←─ toc_nodes(書式アドレス) ＋ 書式頁OCR
P1 転写     ←─ 自炊画像（Box変換 ≤約365MB／超はMac側 or 分割）
```
- **文献OCRが進まない限り P3 は前に進まない**（owner認識と一致）。
- 解説の調達源: ①自炊済み本の解説章（即可・実証済み） ②本丸再自炊（`SCAN_ORDER_honmaru3.md`） ③LIONBOLT＝次PJ（細目次で解説節の頁特定が容易になる）。
- 一冊の見解に偏らないため **source_diversity ≥ 2** を目標とする（複数解説書の合成）。

## 5. パイプライン（v1.0 改訂版）

```
[S1] アドレス確定     式→toc_node→page_span（実証済: 会社議事録321式完全一致）
[S2] P1/P2スナップショット  書式頁vision OCR→form_snapshot.v1（実証済: 3タイプ）
[S2.5] ★解説接地       同書の解説節（toc_nodesで特定）＋法令を OCL
                      → clause_design_knowledge を抽出（引用必須）
[S3] canonical合成     源優先＋粒度ガード＋発明禁止（実装済: 9/9）
[S3.5] ★知識合成       同一条項機能の design_knowledge を複数書から合成
                      （観点の合一/相違を保持。多数決でなく出典別に併記）
[S4] 検証             P2タグ↔P3知識の突合（引用追跡）＋三点測量
[S5] 永続化           form_object＋design_knowledge＋リンク（Mac側承認フロー）
```

## 6. 既存資産（本DDが立脚するもの・全て実証/実装済み）

| 資産 | 状態 |
|---|---|
| 所蔵突合: 出典本101冊中89冊所蔵（書式3,762件分） | DB確認済 |
| 自炊監査: 1,148冊・4点セット規約 | 実地確認済 |
| 環境内vision OCR経路（Box preview, ≤約365MB） | 実証済（3書式＋解説頁） |
| `biblio.toc_nodes`: 弁コム552,544行・sticky ID | ライブ（LIONBOLT=次PJ） |
| S1リゾルバ＋バルクハーネス（7/7・5/5） | 実装済。会社議事録321式anchor確定 |
| form_snapshot.v1（S2標準・3参照実装） | 確定 |
| S3 canonical merge（9/9） | 実装済 |
| L3 PoC: 横断クエリ（機能行列/同機能比較/義務集計/ギャップ検出） | 実証済（限界も記録） |
| 解説接地PoC: 再委託の design_knowledge | 実証済（`poc_grounded/`） |

## 7. ゲート（v0.1から継承＋v1.0追加）

継承: `gate_form_anchor_required` / `gate_sticky_form_uid` / `gate_no_blank_invention` / `gate_snapshot_per_source` / `gate_no_node_invention_in_merge` / `gate_quality_overlay_not_silently_absorbed` / `gate_no_auto_group` / `gate_page_calibration_recorded`
**v1.0追加**:
- `gate_grounding_citation_required` — design_knowledge は grounded_from（出典頁）必須。引用なき設計知識は invalid
- `gate_no_blind_tagging` — P2 functionタグは「暫定」とマークし、P3知識へのリンクなしに正準扱いしない
- `gate_favors_from_context_only` — favors/tightness は解説・法令の記載からのみ付与（書式観測からの推測で付与しない）
- `gate_source_diversity_tracked` — design_knowledge に n_books を記録（単一書由来を明示）

## 8. ロードマップ（owner見立て: P3は「だいぶ先」を前提に）

| 段 | 内容 | 依存 |
|---|---|---|
| R1 | 文献OCRの量産態勢: 本丸再自炊＋自炊済み本の解説章ポイントOCR | スキャン発注済・経路実証済 |
| R2 | 業務委託契約で P3 を1類型ぶん完成（再委託に続き、損害賠償・知財・支払…を同書＋他解説書で接地） | R1の一部 |
| R3 | 複数解説書の知識合成（S3.5）を1機能で実証（source_diversity ≥ 2） | R1 |
| R4 | 条項機能オントロジー正準化（P3知識が貯まってから帰納的に。先験的に作らない） | R2-R3 |
| R5 | コーパス全体への展開・DB化（toc_nodes隣接） | R1-R4＋LIONBOLT(次PJ) |

> **オントロジーを先に設計しない**（v0.1の反省）。設計知識が複数貯まってから帰納的に正準化する。

## 9. owner決定事項（v1.0）

| ID | 問い | 本日の決定 |
|---|---|---|
| D-F5 | 構造の源 | **解説・法令・契約類型から抽出**（書式は一インスタンス）— 採用 |
| D-F6 | P3の中心モデル | **baseline＋押し引き（tighten/loosen × favors）** — 採用 |
| D-F7 | 検証方式 | **引用追跡（grounded_from必須）**でブラインド脱却 — 採用 |
| D-F8 | 律速の認識 | **文献OCRが進まないと書式は前に進まない** — 共有認識 |
| D-F9 | フェーズ認識 | P1転写/P2構造体/P3意味構造。**P3が本来のゴール、ただしだいぶ先** — 共有認識 |

## 10. 監査（お目付け役GPT）に確認したい点

1. clause_design_knowledge の押し引きモデル（baseline/tighten-loosen/favors）は、実務の「条項の押し引き」の表現として十分か。軸の取り方に欠落はないか。
2. `gate_favors_from_context_only`（有利不利は解説からのみ・観測から付与しない）は厳しすぎないか。複数書式の統計的観測を favors の**仮説生成**に使い、解説で確証する二段は許容されるか。
3. オントロジー後置（R4・帰納的正準化）は、先験的設計の失敗を避ける狙いだが、初期の知識蓄積でタグが発散するリスクとのトレードオフをどう見るか。
4. P2構造体（暫定タグ）の大量生産を P3 接地より先行させてよいか（材料先行 vs ブラインド蓄積の懸念）。
