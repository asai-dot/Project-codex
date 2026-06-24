# 評価PoC gold pack 雛形 v0.1（正解パック・採点シート）

- 作成: 2026-06-16 / Claude（リモート）
- 親: `docs/2026-06-14_ai_research_evaluation_design.md`（§2 正解戦略・§3 ベンチ）＋ `docs/2026-06-16_ai_research_eval_rubric_v0.1.md`（C1–C8）
- 用途: 上席弁護士が1問ごとに埋める「正解パック」＋ ALR/HLR ブラインド採点シートの**雛形**。
- **重要（接地原則）**: 本雛形は構造のみ。**判例番号・条番号・書名等は実在を確認できる範囲でのみ記入**し、確認前は `TBF`（to-be-filled）で残す。**架空の典拠を埋めない**（評価自体が捏造を再現しないため。`gate_adopted_value_grounded` の人手版）。

---

## A. gold_pack スキーマ（1問＝1ファイル）

```yaml
task_id:            # 例 EVAL-T3-001
task_type:          # T1条文/時間軸 | T2ドクトリン俯瞰 | T3反対説・不利authority | T4判例系譜 | T5起案支援
question:           # 調査の問い（自然文）。一意に答えるべき範囲を含める
as_of_date:         # 基準日（法のcurrencyはこの日付で判定）。必須
scope:
  jurisdiction:     # 日本
  corpus_boundary:  # 閉じたコーパス（蔵書/弁コム/LION BOLT/legal-library/判例/NDL）。範囲外は C8 で別扱い
difficulty:         # easy | medium | hard

relevant_authorities:        # C1網羅の gold。各々ロケータ必須
  - locator:                 # 条番号 | 判例ID(D1等) | 書名+TOCノード+頁 | 雑誌記事ID
    type:                    # statute_article | case | treatise_section | journal_article
    relevance:               # core | supporting
    in_corpus:               # true | false（false=範囲外。C8用）
    why:                     # なぜ関連か（1行）
    status: TBF|verified

contrary_line:               # C3反対線の gold（★差別化指標の正解）
  - locator:
    stance:                  # 反対説 | 不利判例 | 批判 | 失効/改正で覆る
    in_corpus:
    why:
    status: TBF|verified

issue_map:                   # 論点構造（C6「拾うべき論点」の正解にもなる）
  - issue:
    sub_issues: []
    linked_authorities: []   # 上の locator を参照

expected_pitfalls:           # C4/C5検査用（誤りやすい点）
  - 失効/改正で旧法になった条文:
  - 変更/判例変更された判例:
  - よくある誤引用:

known_unknowns:              # C8用。コーパス外/未決/学説対立で答え無し
  - 

build:
  builders: []               # 上席2名以上
  consensus_method:          # 合議＋裁定（不一致は記録）
  adjudication_notes:
  built_at:
  audit: お目付け役に gold構築設計を載せる（自己採点バイアス回避）
```

### 記入見本（T3・スケルトン / 典拠は TBF のまま＝捏造しない）
```yaml
task_id: EVAL-T3-001
task_type: T3反対説・不利authority
question: 「配偶者居住権を第三者に対抗するための要件と、その実務上の限界について、
          反対・慎重説および不利な裁判例も含めて整理せよ」
as_of_date: 2026-06-01
scope: { jurisdiction: 日本, corpus_boundary: 閉じたコーパス }
difficulty: medium
relevant_authorities:
  - { locator: "民法1031条(配偶者居住権の登記等) [TBF: 現行条文を確認]", type: statute_article, relevance: core, in_corpus: true, why: 対抗要件の根拠, status: TBF }
  - { locator: "[TBF: コーパス内の体系書 該当章節+頁 例『配偶者居住権の法務と税務Q&A』TOCノード]", type: treatise_section, relevance: core, in_corpus: true, why: 実務解説, status: TBF }
contrary_line:
  - { locator: "[TBF: 慎重説を述べる文献節]", stance: 反対説, in_corpus: true, why: 対抗力の実効性に疑問, status: TBF }
  - { locator: "[TBF: 不利な裁判例 判例ID]", stance: 不利判例, in_corpus: TBF, why: 要件を厳格解釈, status: TBF }
issue_map:
  - { issue: 対抗要件(登記)の要否と方法, sub_issues: [登記手続, 第三者の範囲], linked_authorities: [] }
  - { issue: 存続期間と消滅事由, sub_issues: [], linked_authorities: [] }
expected_pitfalls:
  - 失効/改正: 2020年施行の新しい制度＝旧法時代の解説を現行として引かない
  - 誤引用: 配偶者短期居住権との混同
known_unknowns:
  - 「[TBF: コーパス外の最新下級審など]」
```

---

## B. relevance_pool（C1 recall をプール法で算定）

ALR と HLR と gold の典拠を**プール**し、上席が各々に関連判定 → recall は pool 比で計算。

```yaml
task_id: EVAL-T3-001
candidates:
  - locator:
    found_by: [gold|ALR|HLR]   # 複数可
    judge_relevance: relevant | partial | non
    judged_by:
# recall@gold = (ALRが拾った relevant) / (pool内 relevant 総数)
```

---

## C. 採点シート（提出物1本＝ALR or HLR、ブラインド）

```yaml
task_id: EVAL-T3-001
submission_id:               # 採点者にはAI/人を伏せる
condition: F-A(同コーパス) | F-B(現実条件)

gate:                        # 0が一つでもあれば失格・以降採点せず
  C4_grounding: 0..3
  C5_currency:  0..3
  C8_calibration: 0..3
  gate_pass: true|false

scored:                      # 門前通過時のみ
  C1_recall: 0..3
  C2_precision_noise: 0..3
  C3_contrary: 0..3
  C6_beyond_prompt: 0..3
  C7_judgment_ready: 0..3

quantitative:
  recall_at_pool:            # B から
  contrary_recall:           # contrary_line のうち拾えた割合
  grounding_correct_rate:    # 引用箇所が実際にそう述べている割合
  stale_law_errors:          # C5 件数
  novel_valid_issues:        # C6 検証済新規論点数

ambient(該当時):
  issue_surfacing_delta:     # 拾い人が落とした正当論点数
  lead_time:
  noise_tax:

evidence_notes:              # 各スコアの根拠（該当箇所）
```

---

## D. 構築プロトコル（PoC）

1. **題材**: 実依頼案件は使わず**代表的・抽象化した法律問題**で作る（守秘）。必要なら de-identified。
2. **規模**: PoC は T2/T3 各1問＝計2問（評価設計 P1）。
3. **gold構築**: 上席2名で relevant/contrary/issue_map を作成 → 不一致は裁定・記録。
4. **接地**: gold の各典拠は**コーパス内で解決可能**であること（recall を well-defined にする）。範囲外は in_corpus:false で C8 側へ。
5. **ブラインド対比**: 同一問題に ALR と HLR のブリーフ → 採点者は AI/人を伏せて C採点 ＋ pool関連判定。
6. **バイアス回避**: gold構築・採点設計を**お目付け役の独立監査**に載せる（自AIを甘く見ない）。
7. **置き場**: 構造化産物（gold_pack/pool/score）は build/Box（GitHubに置かない）。本雛形(doc)のみ repo。

## E. 接続
- C4 採点 = `gate_adopted_value_grounded` の人手版。gold典拠も全て接地必須＝設計と評価が同じ規律。
- 501本番→属性層 dry-run が回り、論点中間層・引用グラフが揃うほど、本gold packの作成コストが下がる（典拠ロケータが機械で引ける）。
- 次: 501本番後に EVAL-T2-001 / EVAL-T3-001 を実際に1問ずつ埋め、ルーブリックを実問題で較正（評価設計 P2）。
