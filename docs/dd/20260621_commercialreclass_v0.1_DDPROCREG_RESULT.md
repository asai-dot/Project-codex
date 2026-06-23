DDPROCREG_MODIFY_REQUIRED

---
request_file_id: 2299571392411
request_name: 20260621_commercialreclass_v0.1_DDPROCREG_REQUEST.md
source_commit: 53879625d3608bfde96131a684260feef58c6518
source_hash: sha256:207e1315985b6b0f4f36118512e1cf4ee57287302db8697877ec76876a2a814a
gate: DDPROCREG
reviewed_at_jst: 2026-06-22
reviewer: GPT-5.5 Pro / independent code-and-schema audit
verdict: DDPROCREG_MODIFY_REQUIRED
box_from_gpt_file_id: 2301895597251
supersedes_result_version: prior PASS_WITH_NOTES result version on this Box file
---

# GPTお目付け役監査結果 — commercialreclass v0.1

## 0. 総合判定

**再分類の方向は採用するが、本packetのままowner ratify又はL1追記へ進めてはならない。**

組織再編6手続を裁判所の会社非訟から意味上分離し、`corporate_reorganization` family、個別procedure、`ordinary_liquidation`を設ける方向は、親監査 `DDPROGRESS_PASS_WITH_NOTES` と整合する。

しかし、提案差分は次の3点を表現できていない。

1. familyと6 procedureの親子関係がregistry schemaに存在しない。
2. `commercial_nonlitigation`を同一stable IDのまま「会社非訟」に狭めつつ、新familyの`legacy_rollup_id`も同じIDへ向けており、現行意味とlegacy意味が衝突する。
3. 単一実務書観測からowner_ratifiedへ上げる際の、owner固有の法的判断根拠・公式法令anchor・ratification basisが差分に固定されていない。

これは注記だけでは閉じず、実際のregistry意味を変えるため **MODIFY_REQUIRED** とする。

## 1. 親監査との整合

### 1.1 再分類方向 — CLOSED

次の分類方向は妥当である。

- `corporate_reorganization`を会社法上のprocedure familyとする。
- merger / company_split / share_exchange / share_transfer / entity_conversion / share_deliveryを個別procedure候補とする。
- `commercial_nonlitigation`を裁判所による会社非訟procedure群と混同しない。
- `ordinary_liquidation`を特別清算と別procedure候補として扱う。
- 法人類型は原則sparse applicability facetとし、直積展開しない。

### 1.2 L0/L1/L2分離 — PARTIAL

registryはL1、spineはL2、inventoryはL0として分離されている。しかし本packetが提案するfamily membership及びlegacy crosswalkの意味を、現在のL1 schemaは表現できない。

## 2. must_fix

### MF-1 family membershipを規範的に表現する

`procedure_registry.json`の現行entry schemaには`parent_family_id`、`member_of_family`又はtyped relation tableがない。family entryと6 procedureを並べても「配下」にはならない。

次のいずれかをv0.2で固定すること。

```text
A. procedure entryに parent_family_id を追加
B. procedure_family_membership crosswalkを別artifactとして追加
   {family_id, procedure_id, valid_from, valid_to, source_basis, status}
```

validatorで参照先存在、自己参照、循環、kind整合を検査すること。

### MF-2 `commercial_nonlitigation`のstable-ID driftを解消する

同一IDを旧来の広い「商事・会社非訟」から裁判所の会社非訟へ狭める一方、新familyの`legacy_rollup_id`を同じIDへ向けると、次の二つが同時に成立してしまう。

```text
current meaning: commercial_nonlitigation = 裁判所の会社非訟
legacy bridge: corporate_reorganization -> commercial_nonlitigation
```

この状態ではnavigation/crosswalkが組織再編を会社非訟として再表示する。

v0.2では次のいずれかを採用すること。

1. 旧IDをversioned legacy roll-upとして意味変更せず維持し、新たにcourt-company-nonlitigation用IDを作る。
2. 旧IDをdeprecated/supersededとして固定し、会社非訟用と組織再編用の新roll-upへ明示的にsplitする。
3. L2 migration完了までscope narrowingを行わず、L1分類だけ先行する。

stable IDの意味を説明文だけでsilent narrowingしないこと。

### MF-3 owner ratification basisを固定する

単一実務書のL0観測は、現行promotion ruleではcandidate不適格である。ownerは独立判断によりratifyできるが、その場合も単なる`ratified_by/ratified_at`だけでは証拠と判断の区別が残らない。

owner_ratified entryには少なくとも次を要求すること。

```text
ratification_basis_type: owner_legal_judgment | statutory_plus_practice | multi_source
ratification_basis_refs[]
statutory_or_official_refs[]
source_family_refs[]
ratification_note
```

6 procedureについて会社法上の根拠条文又は公式制度資料を固定し、実務書TOCは実務観測として別に残すこと。owner ratifyはcandidate閾値を消すものではなく、誰がどの根拠で例外判断したかを監査可能にする経路である。

### MF-4 ordinary_liquidationの昇格水準

`ordinary_liquidation`のprocedure候補性は高いが、本packetの証拠は単一実務書である。公式/法令anchor又は明示的owner legal judgmentが固定されるまでは`candidate`とする。特別清算との区別、開始契機、終局状態、根拠法及び適用主体を短い操作的定義として持たせること。

## 3. 質問への回答

### Q-A 命名/ID

`corporate_reorganization`及び6 procedure IDは概ね妥当。ただし`entity_conversion`は会社法上の「組織変更」と一対一であることをdefinition/aliasesで固定すること。ID確定はfamily membership schemaと同時に行う。

### Q-B 昇格水準

現状の差分のまま一律`owner_ratified`は不可。まずcandidateとして記録し、各entryについて公式/法令anchor又はowner legal judgment basisを固定したものだけ個別にratifyする。

### Q-C scope縮小

**同一IDのまま無履歴でscope縮小する案は不採用。** versioned legacy又はsupersession/splitが必要である。

### Q-D variant vs facet

単なる対象法人差はentity facet/applicability crosswalk。根拠法、開始主体、必須局面又は終局状態が異なる場合はprocedure_variant又は別procedureとする。名称だけで全法人類型をvariant化しない。

### Q-E 株式交付flow

flow実体は`flow_ref`として紐付けてよい。ただしprocedure identityの独立証拠には数えない。`flow_ref`にはartifact version/hash、source lineage、flow statusを付け、L1 ratificationとflow acceptanceを別ゲートにする。

## 4. should_fix

1. `definition`, `start_trigger`, `terminal_state`, `legal_basis_refs[]`をprocedure entry又は定義artifactに持たせる。
2. family/variant/applicability relationをappend-only/versionedにする。
3. aliasesはidentity証拠でなく検索語彙として明示する。
4. split/merge時の旧crosswalk保全とrollback fixtureを追加する。
5. validatorへfamily membership、ratification basis、stable-ID semantic changeの検査を追加する。

## 5. GO / HOLD

### GO

- v0.2設計patch
- family membership schema/crosswalkの追加
- official/statutory sourceのread-only収集
- candidate entryのdry-run生成
- scope migration及びsupersession mapのfixture
- share_delivery flow_refのversioned設計

### HOLD

- owner_ratified entryの本番追記
- `commercial_nonlitigation`の同一ID silent narrowing
- procedure_spine.jsonの意味変更又は大量改訂
- registry/crosswalkの本番write
- DDL、DB write、canonical promotion、MCP publication、claim support

## 6. final

**DDPROCREG_MODIFY_REQUIRED**

再分類の方向は採用する。v0.2でfamily関係、stable-ID scope migration、owner ratification basisを閉じた後に再投函すること。
