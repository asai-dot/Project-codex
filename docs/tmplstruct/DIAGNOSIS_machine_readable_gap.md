# 診断: 「機械可読な書式構造」はまだできていない — レベル整理とL3の定義

owner指摘(2026-06-11): 書式の**再現(復元)**は人間がPDFを見て打てば済む。AIがやる意味は、
**書式の構造を機械可読(AI-readable)に理解して保持し、その上で人に復元する**こと。
大量の書式を**全て機械可読な構造で持った状態で議論**したい。→ これは今できていない。**同意**。

## レベル整理(今どこにいるか)
| L | 何 | 状態 |
|---|---|---|
| L0 | 文字の再現(transcription) | できる。**人間でもできる＝価値の本体ではない** |
| L1 | restorable_profile（paragraphs＋fixed_spans＋slots＝復元用） | 設計あり(`structure_profile_v0.3.1`)。だが**復元志向** |
| L2 | 形状分類(archetype A–E＋subtype, 3,806件) | 設計あり(`archetype_classifier_v0.3`)。**機械可読だが粗い**(形だけ) |
| **L3** | **深い意味構造**: 条項を**機能(function)で型付け**＋**slotを意味型で**＋**正規化して横断比較可能**にし、**コーパス全体を機械推論/議論**できる | **未構築。これがownerの要求** |

→ 私の `form_object.v1`(blocks＋free-text blanks) は **L0+α**。L1の slot/party_alias/defined_term にすら届かず、L2/L3とも未接続。**ドリフトしていた。**

## 何が本質的に足りないか(L3の中身)
1. **条項機能オントロジー(controlled vocabulary)**: 各条項に「定義/目的/対価/納期/検収/契約不適合(瑕疵)/再委託/秘密保持/知財帰属/損害賠償/解除/期間/反社/準拠法/管轄/完全合意…」の**機能ID**を付与。
   - これが無いと「全契約の“損害賠償”条項を集めて比較」ができない＝議論できない。
2. **意味型slot**: 空欄を free-text ラベルでなく **型付き変数**(party/date/amount_jpy/period_months/jurisdiction_court/ref_別紙/enum…)に。
3. **正規化された比較可能単位**: 同一機能の条項を**横断比較できる正準形**(例: 全“支払”条項を支払期日・方法・遅延損害金率で並べる)。
4. **当事者ロールの型付け**: 甲乙/委託者受託者を role として解決(structure_profileのparty_aliasの発展)。
5. **コーパス・ストア**: N件が**同一スキーマ＋同一語彙**で載り、「機能Xを持つ書式」「上限の無い損害賠償条項」等を**クエリ/クラスタリング/議論**できる。

## 具体例(製造委託基本契約書・私のform_objectから) — L0 vs L3
**いま(L0/L1相当)**:
```json
{"type":"clause","no":"第3条","title":"製造代金",
 "items":["…個別契約に定める製造代金を支払う。消費税等相当額を付加…",
          "…年14.6%の割合による遅延損害金…"], "blanks":[]}
```
**あるべき(L3)**:
```json
{"clause_id":"…:toc:134#c3",
 "function":"payment.consideration", "function_label":"対価・製造代金",
 "obligations":[{"obligor":"委託者","act":"製造代金の支払","trigger":"個別契約の支払期日"}],
 "slots":[{"id":"支払期日","type":"date","source":"個別契約","required":true},
          {"id":"支払方法","type":"enum","source":"個別契約"},
          {"id":"消費税","type":"bool_addon","value":true}],
 "terms":[{"id":"遅延損害金率","type":"rate_pct_pa","value":14.6}],
 "comparable_key":"payment_terms",
 "source_block_ref":"…(L0原文へのアンカー)"}
```
→ こうなって初めて「全業務委託契約の**遅延損害金率の分布**」「**支払方法に銀行振込以外を許す**書式」等を**機械で横断議論**できる。L0は人手で打てる。**L3はAIが理解した証**。

## つまり
- 既存に**形状分類(L2)**と**復元profile(L1)**はある。だが**L3=条項機能オントロジー＋意味型slot＋横断比較可能形＋コーパス推論**は無い。
- 私のform_objectはL3どころかL1にも未達だった。**設計をL3へ引き上げ、既存(archetype/structure_profile)と統合**するのが正しい。

## 提案する次の一手
1. **条項機能オントロジー v0.1** を定義(法務契約の機能タグ集合＋ID＋同義語)。これがL3の背骨。
2. `form_object` を **L3スキーマ**へ拡張(clause.function / typed slots / obligations / terms / comparable_key)。既存structure_profileのslot/party_alias定義を継承。
3. 完成済み2書式をL3で**手作業エンコード**して、横断クエリの素振り(例: 支払条項の比較)を1つ実演 → 「機械で議論できる」を実証。
4. その後にコーパス展開(まずarchetype A=契約の条項機能タグ付け)。

要は、**「復元できる」から「機械が構造を理解して保持し、コーパスで議論できる」へ軸を移す**。これがご指摘の核心だと理解しました。
