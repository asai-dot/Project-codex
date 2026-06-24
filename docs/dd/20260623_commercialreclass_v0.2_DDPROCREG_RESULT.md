DDPROCREG_MODIFY_REQUIRED

---
request_file_id: 2305878803426
request_name: 20260623_commercialreclass_v0.2_DDPROCREG_REQUEST.md
request_sha1: 59f7b5e3a705d46d87f325d32f8a75543cbdecff
request_source_hash: sha256:4603f3eca72f8be382e91d7c16d60013470e2ab85787ab56372ad5da1a3289bf
packet_commit: 9a100e1e92b9d2d95d1ce659eef8c13f50e265d3
implementation_commit: 89e21ec6093faf8f807120f9360797094b6c4d3e
prior_request_file_id: 2299571392411
prior_result_file_id: 2301895597251
prior_verdict: DDPROCREG_MODIFY_REQUIRED
gate: DDPROCREG
reviewed_at_jst: 2026-06-24
reviewer: GPT-5.5 Pro / independent schema-and-code audit
verdict: DDPROCREG_MODIFY_REQUIRED
box_from_gpt_file_id: 2305936648652
---

# GPTお目付け役監査結果 — commercialreclass v0.2

## 0. 総合判定

**再分類の方向、family membership、stable-IDを据え置く選択、通常清算をcandidateに留める扱いは採用できる。**

しかし、前回must_fix MF-3（owner ratification basis）は、説明文上は反映されているものの、実際のvalidatorとtestでは閉鎖していない。現在の実装は、`owner_legal_judgment`と任意のowner note参照だけで`owner_ratified`を通せる。前回RESULTが要求した公式・法令anchor及びsource-family provenanceを欠いたままL1昇格できるため、v0.2のratify/design acceptanceはHOLDとし、**MODIFY_REQUIRED**とする。

本判定は再分類案そのものを否定するものではない。MF-1、MF-2、MF-4はv0.3の基礎として維持してよい。

## 1. 前版must_fixの閉鎖判定

### MF-1 family membership — CLOSED WITH NOTES

`family_membership` crosswalkを採るoption Bは十分であり、`parent_family_id`との二重管理は不要である。

実装はfamilyから6 procedureへの関係を明示し、validatorは参照存在、kind整合、自己参照、重複を検査している。family/memberのkindを排他的にしているため、現行一階層モデルでは循環も構造上生じない。

ただし次は追加することが望ましい。

- `valid_from`必須、`valid_to > valid_from`又はnullの検査
- `source_basis`必須・空文字禁止
- membership statusと両端entry statusの整合
- 同一family/procedureについて有効期間の重複禁止

### MF-2 stable-ID drift — CLOSED FOR v0.2

`commercial_nonlitigation`を`keep_unchanged`として意味を狭めず、court会社非訟用の新ID/splitをowner判断及びL2 migrationまでHOLDする選択は妥当である。前回が許容した「L2 migration完了までscope narrowingを行わず、L1分類だけ先行する」経路に該当する。

現行データについてsilent narrowingはない。

なお将来用guardは、単なるsupersession stubの存在だけでなく、少なくとも旧ID、後継ID群、action、validity、理由、rollback/crosswalk fixtureを要求するよう強化することが望ましい。

### MF-3 owner ratification basis — NOT CLOSED / BLOCKING

registryの説明文は、owner-ratified entryに次を付けるとしている。

- `ratification_basis_type`
- `ratification_basis_refs`
- `statutory_or_official_refs`
- `source_family_refs`
- `ratification_note`

しかしvalidatorの実装は、次だけを要求している。

```text
ratification_basis_type
ratification_note
ratification_basis_refs OR statutory_or_official_refs
```

このため、`statutory_or_official_refs`も`source_family_refs`も空のまま昇格できる。実際のpositive testも、`owner_legal_judgment`、`ratification_basis_refs: ["owner note 1"]`、noteだけで健全と判定している。

これは前回RESULTの「6 procedureについて会社法上の根拠条文又は公式制度資料を固定し、実務書TOCは実務観測として別に残す」「少なくともbasis type / basis refs / statutory-or-official refs / source-family refs / noteを要求する」に反する。

#### v0.3必須修正

`owner_ratified`について、少なくとも次を全てnon-emptyで要求すること。

```text
ratified_by
ratified_at
ratification_basis_type
ratification_basis_refs[]
statutory_or_official_refs[]
source_family_refs[]
ratification_note
```

加えて、procedure entryはratify時に`legal_basis_refs[]`もnon-emptyとし、各参照は可能ならURI/citation、source family、snapshot又はhashを持つ構造化refにすること。

テストは各フィールドを一つずつ欠落させたnegative fixtureを持ち、owner noteだけのpositive fixtureは削除すること。完全な根拠集合だけをpositiveとする。

### MF-4 ordinary_liquidation — CLOSED AS CANDIDATE

`ordinary_liquidation`はcandidateに留まり、特別清算と別procedureであること、開始契機、終局状態、株式会社への適用が操作的定義から読める。candidate段階としては妥当である。

ただし`legal_basis_refs`は空であるためratify不可であり、MF-3のvalidator修正により機械的に止めること。適用主体は自由文だけでなく`applicable_entity_types[]`等のfacetに分離することが望ましい。

## 2. 追加監査所見

### 2.1 canonical境界の明示

`procedure_registry.json`は`L1_registry`及び「正準レジストリ」と称する一方、単一sourceでpromotion_report上candidate不適格の8件を`status: candidate`として格納している。本packetはdry-runでありproduction writeではないため直ちにcanonical逆行とは扱わないが、誤昇格を避けるため次のいずれかを固定すること。

1. dry-run候補を別artifactへ分離する。
2. `registry_mode: design_fixture` / `materialization_status: noncanonical`等を付け、production loaderが拒否する。
3. `proposed_candidate`とpromotion-ruleを満たした`candidate`を別statusにする。

### 2.2 flow_ref provenance

`share_delivery.flow_ref`はpath、draft status、別ゲート注記まで閉じているが、前回Q-Eが求めたartifact version/hash及びsource lineageがない。`artifact_version`、`artifact_hash`、`source_lineage`を追加し、flow acceptanceとL1 ratificationを別ゲートのまま維持すること。

### 2.3 provenance pointer

Box REQUESTの`git_commit`はpacket commit `9a100e1...`を指す一方、実装は`89e21ec...`にある。再現性のため、次回は`packet_commit`と`implementation_commit`を別フィールドにすること。

### 2.4 test evidence

実装commitにGitHub Actions status/workflowは付いていない。REQUESTの「全緑」はlocal runの申告として扱った。再投函時は実行コマンド、終了コード、check数、commit SHAを含む短いtest logを同梱するとよい。

## 3. REQUEST質問への回答

1. **MF-1** — option Bの`family_membership`だけでよい。option Aとの併用は不要。ただしvalidity/source/status整合validatorを補強する。
2. **MF-2** — `keep_unchanged`で据え置き、新ID/splitをowner+L2 migration待ちとする選択は妥当。
3. **MF-3** — 現在のtype/refs/note粒度及びvalidatorは不十分。公式・法令refsとsource-family refsを必須化する。
4. **MF-4** — candidateとしてのdefinition/start_trigger/terminal_stateは概ね十分。legal basisと構造化applicabilityを固定するまでratify不可。

## 4. GO / HOLD

### GO

- v0.3の限定patch
- MF-1/MF-2/MF-4実装をpatch baseとして維持
- ratification validator及びnegative fixturesの補強
- official/statutory sourceのread-only収集
- candidateのscratch/design-fixture dry-run
- membership validity、supersession、flow provenanceのfixture追加

### HOLD

- v0.2のratify又はaccepted/canonical promotion
- `owner_ratified` entryの追記
- 単一source候補の正準L1 materialization
- `commercial_nonlitigation`のscope縮小又はspine意味変更
- registry/crosswalkのproduction write
- DDL、DB write、MCP publication、claim-support利用

## 5. 再監査の最小受入条件

1. owner-ratified validatorが全必須根拠フィールドをnon-emptyで要求する。
2. owner noteだけのfixtureがfailし、完全根拠fixtureだけがpassする。
3. procedure ratify時の`legal_basis_refs`必須化。
4. candidate dry-runとcanonical L1の境界を機械可読に固定する。
5. test logをsource commitと結び付けて同梱する。

## 6. final

**DDPROCREG_MODIFY_REQUIRED**

再分類設計は採用方向。v0.3でMF-3及びcanonical境界を閉じた後に再投函すること。
