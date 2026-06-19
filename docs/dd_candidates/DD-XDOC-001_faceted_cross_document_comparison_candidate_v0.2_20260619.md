# DD-XDOC-001 v0.2 — faceted cross-document comparison & alignment（MODIFY反映）candidate

> **id**: DD-XDOC-001 / **version**: candidate v0.2 / **supersedes**: v0.1
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/production clustering/FRBR・LITLINK 自動昇格は HOLD。
> **改訂理由（v0.1→v0.2）**: GPT Pro 監査 `DDXDOC_MODIFY_REQUIRED` 反映。独立DDの位置づけ（XDOC＝文書間・同一facet比較）は是認。must-fix 8点を反映。
> **depends_on**: DD-LAYOUT-001 v0.5 accepted（安定アンカー・coverage・block_ref）, DD-XMODAL-001 v0.4 accepted（external_source_family registry・独立性）, DD-LITID-001, DD-LITLINK-001, 三軸 v0.3。

---

## 0. must-fix 反映サマリ
| # | GPT must-fix | v0.2 反映 |
|---|---|---|
| 1 | external_source_family 不十分。内容起源 vs 観測パイプライン依存を分離 | §1（2軸 dependency） |
| 2 | xdoc_alignment を方向付き・多対多・edit script 対応に | §2 |
| 3 | MinHash/embedding/CDC の能力範囲を分け、table と figure を別手法 | §3 |
| 4 | DD-LAYOUT coverage 継承。未抽出を差分・不存在と誤認しない | §4 |
| 5 | block_ref / DD-LITLINK / xdoc_alignment の所有境界を明示 | §5 |
| 6 | 単一 facet から FRBR Work 同一性へ昇格しない | §6 G_XDOC_NO_SINGLE_FACET_WORK_ID |
| 7 | pairwise similarity の推移閉包による巨大 cluster 化を禁止 | §6 G_XDOC_NO_TRANSITIVE_MEGACLUSTER |
| 8 | 人手判定を 4種に分ける | §7 |

## 1. ★依存の2軸分離（must-fix#1）
「独立」を1次元で測らない。一致が以下のどちらかを共有していれば**独立裏付けでない**：
```text
content_origin_family    # 内容起源：同一条文・判例・原稿・編者テキスト
pipeline_family          # 観測パイプライン：同一 OCR エンジン・parser・スキャン源・正規化 profile
```
- `independent` 判定＝**両軸とも distinct**（DD-XMODAL の external_source_family registry を**2軸に拡張**）。
- 例：2冊が同一条文を引く＝content 共有→1源。2冊が同一 OCR で読まれた＝pipeline 共有→観測相関。どちらも「独立2源」と数えない。
- **G_XDOC_DEP_TWO_AXIS**：independence は content_origin_family ∧ pipeline_family の両 distinct を要求。

## 2. ★xdoc_alignment の再設計（must-fix#2）
1対1単純 pair をやめ、**方向付き・多対多・edit script 対応**に：
```text
xdoc_alignment                    # 派生・claim_support_eligible=false
  alignment_id ; facet∈{structure,text,table,figure}
  direction∈{a_to_b, b_to_a, symmetric}
  cardinality∈{1:1, 1:n, n:1, n:m}
  members_a[unit@asset...] ; members_b[unit@asset...]    # 多対多
  edit_script[]            # structure: insert|delete|move|rename|split|merge（tree edit 由来）
  similarity ; method ; method_version
  coverage_ref             # §4
  dependency{content_origin_families[], pipeline_families[], independent:bool}   # §1
  status∈{candidate,reviewed,accepted,rejected}
```

## 3. ★手法の能力範囲を分離（must-fix#3）
**何を主張できるかを method 毎に宣言**（混同禁止）：
| method | facet | 主張できること | できないこと |
|---|---|---|---|
| **MinHash/SimHash** | text | 近重複・集合類似（語の重なり） | 意味同一・引用方向 |
| **embedding** | text | 意味的近接 | 記号一致・逐語同一 |
| **CDC/Rabin** | text | content-addressed 区間同一（byte/char） | 意味・言い換え |
| **table structure matching** | table | 表の行列構造・セル対応 | 図的内容 |
| **figure method**（pHash / visual embedding） | figure | 画像近接・図版同一 | 表構造・記号 |
- **G_XDOC_METHOD_CAPABILITY_DECLARED**：alignment は method の capability を宣言し、能力外の主張をしない。table と figure は**別手法**（束ねない）。

## 4. ★coverage 継承（must-fix#4）
DD-LAYOUT の projection coverage を継承。**未抽出（未型付け/未OCR）を「差分」や「不存在」と誤認しない**。
```text
coverage_ref -> {asset, facet, blocks_typed, blocks_untyped, scope_coverage}
# 比較で「片方に無い」場合、coverage が不完全なら difference でなく unknown
```
- **G_XDOC_COVERAGE_INHERITED**：coverage 不完全域は absent/diff と断定せず `unknown` を返す。

## 5. ★所有境界の明示（must-fix#5）
| レイヤ | 所有 DD | 守備範囲 |
|---|---|---|
| `block_ref` | **DD-LAYOUT** | 文書内・別紙間の**参照**（脚注/図/別紙） |
| `lit_link` | **DD-LITLINK** | 文献→**外部/法的オブジェクト**（法令/判例/語彙） |
| `xdoc_alignment` | **DD-XDOC（本DD）** | 文書間・**同一 facet の比較/整列** |
- **G_XDOC_OWNERSHIP_EXPLICIT**：3者を混ぜない。XDOC は推定 alignment のみ所有し、参照(block_ref)・外部リンク(LITLINK)を生成・改変しない（候補を渡すのみ）。

## 6. 昇格・クラスタの制約（must-fix#6,#7）
- **G_XDOC_NO_SINGLE_FACET_WORK_ID**：単一 facet の一致から **FRBR Work 同一性へ昇格しない**（Work 同定は多 facet＋人手）。
- **G_XDOC_NO_TRANSITIVE_MEGACLUSTER**：pairwise similarity の**推移閉包で巨大 cluster を作らない**。`xdoc_cluster` は最小密度・最大サイズ・transitive 禁止（A~B, B~C から A~C を自動結合しない）。人手 or 明示的 consensus でのみ確定。

## 7. ★人手判定の4分割（must-fix#8）
単一の「採用/却下」をやめ、4つの独立判定に分ける：
```text
human_review:
  alignment_correctness   # その整列は正しいか（同じ箇所か）
  relation_interpretation # 整列の意味（引用/版違い/同論点/転載）
  independence            # 独立裏付けか（§1 2軸）
  downstream_usability    # 下流利用可否（LITLINK/FORMOBJ/FRBR 候補に渡してよいか）
```

## 8. 不変（v0.1 承継）＋ 出力
facet 別比較（structure/text/table/figure）。出力は全て **candidate・evidence 昇格禁止**（文献chunk は supporting_analysis 止まり）・自動正準化しない。inventory-probe（facet 別 yield・shared_source 率・**pipeline_shared 率**を実測）。

## 9. ゲート一覧
G_XDOC_DERIVED / NO_CLAIM_SUPPORT / HUMAN_PROMOTION_ONLY / NO_SELF_LOOP / FACET_ANCHORED（v0.1）
＋ **DEP_TWO_AXIS / METHOD_CAPABILITY_DECLARED / COVERAGE_INHERITED / OWNERSHIP_EXPLICIT / NO_SINGLE_FACET_WORK_ID / NO_TRANSITIVE_MEGACLUSTER**（v0.2）。

## 10. open items / loop_state
O1 facet 別手法・閾値／O2 asset 同定 DD-LITID 接続／O3 shared_source（content/pipeline 両軸）検出の実装／O4 edit_script 生成（tree edit）／O5 cluster の非推移的確定法。
loop_state = **patched（v0.2）→ 再投函（再監査）候補**。HOLD：DDL/DB/mint/embedding/production clustering/FRBR・LITLINK 自動昇格。
