DDPROGRESS_PASS_WITH_NOTES

source_request_file_id: 2294941156684
source_request: 20260619_spinebottomup_v0.1_DDPROGRESS_REQUEST.md
reviewed_at_jst: 2026-06-19
reviewer: GPT-5.5 Pro
gate: DDPROGRESS
scope: spine bottom-up direction review only
execution_scope: no spine canonical rewrite, no DDL, no DB write, no requirement_floor promotion, no MCP publication
verdict: DDPROGRESS_PASS_WITH_NOTES

## 0. 総合判定

方向性は正しい。a-priori に置いた24類型を、実務書TOC由来の観測で反証・分割・補完する `procedure_inventory` + `spine_reconcile.py` のレーンは続行してよい。

ただし、次の結論表現は弱める必要がある。

```text
現状で実証されたこと:
- 商事系の現行umbrellaに粒度・分類上の問題がある。
- 通常清算という未収容procedure candidateがある。
- 法人類型という直交facetが必要になる可能性が高い。

まだ実証されていないこと:
- 24類型全体が粗すぎる。
- 現サンプルで未観測の22類型に裏付けがない。
- TOC由来inventoryをそのまま正本にできる。
```

最終推奨は、既存spineかinventoryのどちらか一方を正本にする二者択一ではない。次の三層に分ける。

```text
L0 procedure_observation:
  TOC・法令・公式案内から得た観測。raw heading、kind、source、位置を保持。

L1 procedure_registry:
  操作的定義を満たし、owner ratifyされたprocedure / family / variant。
  安定IDを持つ正準レジストリ。

L2 procedure_rollup_and_facets:
  旧24類型のnavigation spine、系統、法人類型、forum、目的等のroll-up/facet。
  用途別ビューであり、唯一の真理にしない。
```

したがって、**bottom-up化はGO**。ただし、既存24類型は互換性のあるroll-upとして残し、raw inventoryは観測層に留め、owner-ratified registryを間に置くこと。

## 1. Findings

### Q1. spine の位置づけ

**三層化を推奨。**

- a-priori 24類型をcanonical procedure listのまま維持するのは粗い。
- 逆に、3冊由来のinventoryを直ちに正本化するのはサンプル依存が強すぎる。
- 現行spineは `legacy_rollup_id` / navigation facetとして残す。
- procedure registryは、複数sourceまたは法令・公式案内・owner reviewで昇格する。

推奨status:

```text
observed
candidate
owner_ratified
superseded
deprecated
```

### Q2. 「商事・会社非訟」の分割

**分割方向は妥当だが、現 `spine_ref=commercial_nonlitigation` のまま6手続へ割るのは不可。**

合併、会社分割、株式交換、株式移転、組織変更、株式交付は、会社法上の組織再編・会社行為・登記手続であり、すべてが裁判所の「商事・会社非訟」ではない。現在の対応は、粒度問題に加えてcategory errorを含む。

推奨:

```text
procedure_family: corporate_reorganization
procedures:
  merger
  company_split
  share_exchange
  share_transfer
  entity_conversion
  share_delivery

commercial_nonlitigation:
  検査役選任等の裁判所非訟手続を別に維持
```

つまりF1は「会社非訟を6分割」とせず、**会社法手続familyの新設・再分類**としてowner reviewに出す。

### Q3. 法人類型の直交軸

**追加すべき。ただし全組合せを実体化しない。**

手続 × 法人類型を巨大な直積表にせず、疎なapplicability crosswalkとする。

```text
procedure_applicability:
  procedure_id
  entity_type
  applicability_status
  condition
  source_basis
```

共通の目的・terminal state・骨格を保つなら `procedure_variant`。根拠法・主体・終局状態が別なら別procedure。単なる対象法人差ならfacetに留める。

### Q4. TOC level と kind

`kind`を置く方針は正しいが、操作的定義が必要。

推奨enum:

```text
procedure_family:
  複数procedureを束ねるnavigation単位。

procedure:
  固有の目的、開始契機、一定の法的/実務的根拠、局面列、終局状態を持つ過程。

procedure_variant:
  同じprocedureの目的・終局を共有するが、主体・法人類型・選択route等で局面が分岐するもの。

flow_step:
  procedure内部の局面。単独でprocedure IDを鋳造しない。

dimension:
  entity type、forum、公開/非公開等の直交facet。
```

TOC headingは `procedure candidate` を作る証拠であって、それだけでprocedure確定ではない。

### Q5. 次の一手

**spine意味モデルの補正を先にgateする。ただしe-Gov各号のread-only取得は並行してよい。**

優先順位:

```text
1. reconcile reportの意味補正と三層モデル案を作る。
2. 商事系再分類・通常清算・entity_type facetをowner packetにする。
3. 複数独立書籍・法令・公式案内でinventoryを拡張する。
4. owner ratify後にprocedure registry / roll-upを改訂する。
```

`requirement_floor` 用のe-Gov条文各号取得は、law/article/item anchorとして再利用可能でありread-onlyなら並行着手可。ただし、未確定procedure IDへのcanonical mapping、floor accepted化、DB writeはHOLD。

## 2. must_fix

次のowner review packetまたはv0.2で必ず修正すること。

1. `inventory_procedures=10` を修正する。現10項目は `procedure=8 / dimension=1 / flow_steps=1`。`inventory_items`と`procedure_items`を分ける。
2. `inventory_unmapped` をkind別に分ける。法人類型dimensionを「未マップ実手続」と呼ばない。
3. `spine_no_evidence` を `not_observed_in_current_sample` に改称する。3冊の未観測は「裏付け無し」ではない。
4. reportに `source_book_count / source_family_count / domain_coverage` を出す。
5. 組織再編6手続を `commercial_nonlitigation` に直接紐付けず、company-law / corporate-reorganization familyへ再分類する。
6. raw observation / owner-ratified procedure registry / roll-up facetを分離する。
7. 1冊・1章だけからprocedureをauto-acceptしない。

## 3. should_fix

1. 各observationに `source_toc_node_id`, `heading_raw`, `heading_level`, `source_page`, `extraction_version` を持たせる。
2. 同一上流を重複証拠として数えないため `source_family` を持つ。
3. candidate昇格条件を定義する。例: 独立2source、または法令/公式1source + 実務書1source。
4. `spine_reconcile.py` にkind別集計、source coverage、confidenceを追加する。
5. stable procedure IDのsplit/mergeにはsupersession mapを作り、既存crosswalkを壊さない。
6. 「24類型は粗すぎることが実証」という文言を「商事系の過少解像と欠落が初回サンプルで確認」に直す。

## 4. GO / HOLD

GO:

- bottom-up procedure observation の継続収集
- reconcile tool / report semantics の修正
- procedure registry + roll-up/facet 三層設計
- 商事系・通常清算・entity typeのowner review packet作成
- e-Gov条文各号のread-only取得とraw保存
- dry-run crosswalk / coverage report

HOLD:

- procedure_spine.json の正本置換・大量改訂
- inventoryからの自動procedure確定
- 組織再編6手続のcommercial_nonlitigation配下での確定
- requirement_floorのaccepted化・canonical mapping
- DDL / DB write / production rollout
- MCP publication / claim support

## 5. final

```text
DDPROGRESS_PASS_WITH_NOTES

bottom-up direction: GO
current 24-type spine: retain as versioned roll-up, not sole canonical truth
raw inventory: observation layer only
owner-ratified procedure registry: add between observation and roll-up
commercial finding: reclassify, do not merely split company-nonlitigation
entity-type axis: GO as sparse facet/variant, not full cartesian matrix
e-Gov item acquisition: parallel read-only GO
canonical spine rewrite / DDL / DB / floor promotion: HOLD
```

以上。
