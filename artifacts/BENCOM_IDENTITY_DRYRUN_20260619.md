# bencom identity 突合 — 実作業完了レコード (rev4 §11)

- generated_at_jst: 2026-06-19
- target: Supabase project `nixfjmwxmgugiiuqfuym` / schema `bookdx`
- method: `apply_migration` 適用済み + `execute_sql` で検証 (read-back)
- status: **本丸 (DB 不整合解消) 完了**。残 2 点 (本ファイルの記録 / review ビュー) を本コミットで永続化。

> 注: 本ファイルは、Box `02_LIT_PHASE0_IDENTITY_DRYRUN_20260617.md` の rev4 (= rev3 本文 +
> §11) として記録するはずだった内容を、Box 書込承認ゲートが解除されなかったため
> リポジトリ側に退避したもの。Box への反映は承認が下り次第 `upload_file_version` で実施する。

---

## サマリ (適用・検証済み)

| 作業 | 件数 | 検証 |
|---|---|---|
| `holding_bencom_link` (bencom_id 橋) | 1,737 | ✅ read-back 一致 |
| scanned フラグ付与 | 611 | ✅ |
| `books` ↔ `authpub` 橋 | 3,798 | ✅ |
| セキュリティ硬化 (RLS / view 権限) | — | ✅ advisors 再チェック済み |
| holdings 総数 (参考) | 6,524 | ✅ 2026-06-19 時点 |

## §11 — identity 突合の確定ロジック (記録)

1. 突合キー = `(title_norm, publisher_norm)` を空白 (半角/全角) 除去・小文字化した
   fingerprint。ISBN がある場合は ISBN を優先キーとする。
2. fingerprint が **一意** に candidate と対応する holdings のみ自動リンク (1,737)。
3. fingerprint が **複数 holdings 間で衝突** するものは自動リンクせず、人手レビュー
   キューへ回す (FP 監査方針: 衝突は人間判断)。→ 下記 review ビュー。
4. リンクは `bookdx.holding_bencom_link (internal_id, book_id)` に挿入。

## review ビュー DDL (承認下り次第 apply、または SQL Editor で実行可)

```sql
create or replace view bookdx.v_holding_bencom_review as
with hold as (
  select internal_id, title, publisher, isbn, coalesce(isbn,'')<>'' as has_isbn,
    lower(regexp_replace(coalesce(title_norm,''),'[[:space:]　]','','g')) tk,
    lower(regexp_replace(coalesce(publisher_norm,''),'[[:space:]　]','','g')) pk
  from bookdx.holdings),
grp as (
  select tk,pk,count(*) c from hold where tk<>'' group by tk,pk having count(*)>1),
cand as (
  select distinct on (tk,pk) book_id, title as cand_title, publisher as cand_publisher,
    lower(regexp_replace(coalesce(title_norm,''),'[[:space:]　]','','g')) tk,
    lower(regexp_replace(coalesce(publisher_norm,''),'[[:space:]　]','','g')) pk
  from bookdx.candidates where coalesce(title_norm,'')<>'')
select h.internal_id, h.title, h.publisher, h.isbn, h.has_isbn,
       g.c as holdings_sharing_key,
       cm.book_id as candidate_book_id, cm.cand_title, cm.cand_publisher
from hold h
join grp  g  on g.tk=h.tk and g.pk=h.pk
join cand cm on cm.tk=h.tk and cm.pk=h.pk
order by h.title, h.internal_id;

comment on view bookdx.v_holding_bencom_review is
  'Review queue: holdings whose (title,publisher) fingerprint is shared by multiple holdings (collision) AND matches a bencom candidate. NOT auto-linked (FP audit: collisions to human review). Disambiguate by ISBN/page_count/edition then insert into bookdx.holding_bencom_link. 2026-06-19.';
```

## 運用: review キューの捌き方

1. `select * from bookdx.v_holding_bencom_review;` で衝突候補を一覧。
2. ISBN / page_count / 版表示で 1 件に確定。
3. `insert into bookdx.holding_bencom_link (internal_id, book_id) values (...);`
4. 再実行で当該 fingerprint がキューから外れることを確認。

## 残タスク (承認が必要)

- [ ] 本 §11 内容を Box `02_LIT_PHASE0_IDENTITY_DRYRUN_20260617.md` rev4 として反映
      (`upload_file_version`、書込承認待ち)。
- [ ] `v_holding_bencom_review` を本番へ apply (`apply_migration`、書込承認待ち)。
- [ ] review キューの人手確定 (Owner 作業)。
