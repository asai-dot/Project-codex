DDLAWREF_PASS_WITH_NOTES

# GPT Pro RESULT: DDLAWREF v0.1 design audit

request_id: DDLAWREF_v0.1_20260623
request_file_id: 2305327616655
reviewed_at_jst: 2026-06-24
label: DDLAWREF_PASS_WITH_NOTES
verdict: PASS_WITH_NOTES

## 1. 結論

本件は PASS_WITH_NOTES。

法令オブジェクトに、形式軸 DD-LAWTIME、実質軸 DD-LAWSUBTRANS に続く第三軸として「接続軸」を切り出す設計は妥当である。

ただし、接続軸はあくまで形式事実 edge として扱う。委任の限界、趣旨、違法性、解釈上の射程といった評価を edge に混ぜてはいけない。評価は DD-LAWSUBTRANS / assertion layer に送る。この線引きが守られる限り、design accept でよい。

## 2. §2 の4判断への回答

### 2.1 第三軸の切り出し

妥当。

法令間接続は、時間軸とも実質評価とも違う。

- 法律から政令・省令への委任
- 条文間参照
- 読替え
- 実施・根拠関係
- 告示・通達・行政解釈との接続

これらは「ある条文が、どの法令・条文・行政文書に接続しているか」という形式的ネットワークである。形式事実 edge として `alo_edges` / link layer に引き取る方針は正しい。

ただし、edge_type は絞るべきである。v0.1 では以下程度でよい。

- delegates_to
- references
- implements
- reads_as
- authority_basis
- cites_statute
- cites_administrative_guidance

`reads_as` は読替え専用に限定する。一般的な解釈・評価に広げると、形式 edge が一気に泥団子になる。

### 2.2 OSS 戦略

妥当。

参照抽出の本体を Lawtext に寄せ、略称名寄せ等を部品流用し、委任 typing と限界評価だけ自前にする方針は、ゼロイチを避ける実務的な設計である。

特に `analysis_law_reference` を「参照抽出器」と誤認せず、src 精読で略称辞書ビルダーと訂正した点は評価できる。ここを見ないまま採用していたら、鍋のつもりで蓋だけ買う事故だった。

ただし、OSS 採用前に次を固定すること。

1. version / commit hash
2. license
3. parser input / output contract
4. failure mode
5. 日本法特有表記への対応範囲
6. ALO 側で吸収する差分

### 2.3 改め文を delta_kind の公式真実源にする点

妥当。

条文 text-diff は、見かけの差分は取れるが、法的な改正行為の種類を正確に表すとは限らない。改め文・新旧対照表を真実源にし、text-diff を補助・検算・候補生成へ降格する判断は正しい。

gold を改め文 / 新旧対照表から機械生成し、人手は spot 監査に限定する方針も、スケールする。

ただし、production 前には実改正の改め文で minimum gold set を作ること。合成改め文だけでは、表記揺れ・準用・読替え・枝番・削除後繰上げの地雷を踏めない。

### 2.4 L4 同定の地盤

妥当。

3表記を単一正準 article_path に集約し、版間 crosswalk を確度付き assertion として持つ設計は正しい。

版間同一性を「事実」として即断しない点が重要である。実データで誤 join 740→774 を炙り出したなら、なおさら断定型 canonical merge は危険。crosswalk は evidence-backed assertion として、confidence / source / parser_version / review_status を持たせるべきである。

## 3. blocking ではないが必須の notes

### 3.1 edge と assertion を分ける

DDLAWREF の edge は形式接続だけを持つ。

入れてよいもの:

- どの法令・条文がどれを参照するか
- どの条文が委任根拠になっているか
- どの行政文書がどの条文を根拠にするか
- どの条文が読替え対象か

入れてはいけないもの:

- 委任の限界を超えるか
- 委任の趣旨に合うか
- 当該通達が裁判規範として妥当か
- その行政解釈が優越するか

後者は assertion / legal evaluation layer に送る。

### 3.2 source provenance を必須にする

各 edge には、少なくとも次を持たせる。

- source_system
- source_version
- source_document_uri
- source_text_span or pointer
- parser_version
- extraction_method
- confidence
- review_status
- fetched_at or snapshot_id

unknown を根拠にしない。推測で埋めない。これは家風というより、データベースが嘘つきにならないための酸素である。

### 3.3 edge_type taxonomy は lawtime と統合管理する

DDLAWREF は DD-LAWTIME / lawtime placement と衝突しやすい。

特に `cites_statute`、`references`、`delegates_to`、`implements` は lawtime 側の citation edge と共有語彙にすること。

edge_type registry を作り、各 edge_type について次を定義する。

- definition
- allowed src_type
- allowed dst_type
- source eligibility
- whether temporal evaluation is required
- claim_support default
- evaluation layer handoff rule

### 3.4 行政解釈レイヤは慎重に分ける

告示・通達・ガイドライン・Q&A・逐条解説的資料は、法令とは authority が違う。

同じ `alo_edges` に載せてもよいが、node_type / source_authority / binding_status / publication_status を分けること。

行政文書を「法令」と同じ顔でLLMに渡すと、後で必ず事故る。ラベルの服を着た狼になる。

### 3.5 production 前の gold 条件

production gate 前に、最低限以下の gold set を作る。

- 委任チェーン: 法律→政令→省令の明示例
- 条文間参照: 同一法内・別法間の双方
- 読替え: 準用・みなし・読替えの典型例
- 改め文 delta_kind: 実改正の追加・削除・置換・繰上げ・枝番
- 行政解釈: 根拠条文が明示される通達 / ガイドライン
- negative examples: 参照らしく見えるが edge 化しないもの

## 4. Gate 判断

- 第三軸として接続軸を切る: GO
- 接続軸を形式事実 edge に限定: GO
- 委任限界・趣旨評価を assertion 側へ送る: GO
- Lawtext 中心の OSS 戦略: GO WITH NOTES
- analysis_law_reference の役割訂正: GO
- 改め文を delta_kind truth source にする: GO
- text-diff を補助に降格: GO
- 3表記→正準 article_path: GO
- 版間 crosswalk を confidence付き assertion にする: GO
- production DDL / DB write: HOLD
- claim_support serving: HOLD
- 実改め文 gold なしで本番化: NO

## 5. 修正要求ではなく反映 notes

v0.1 notes に次を追記すれば design accept としてよい。

1. edge_type registry の最小表。
2. `reads_as` を読替え専用に限定する注記。
3. administrative guidance node の authority / binding status 分離。
4. lawtime edge_type と DDLAWREF edge_type の統合管理。
5. production 前 gold set の内訳。
6. source provenance 必須項目。
7. unknown を claim_support に使わない gate。

## 6. 最終ラベル

DDLAWREF_PASS_WITH_NOTES

設計は採用可。形式接続 edge と実質評価 assertion の分離を維持し、edge_type registry、provenance、gold set、administrative guidance の権威差分を追記して次へ進めること。production は別ゲート。
