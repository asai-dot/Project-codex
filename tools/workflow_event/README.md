# alo-workflow-event

ALO workflow event envelope (`docs/workflow_model`) の **v0.2 schema** を
**python3 標準ライブラリのみ**で検証する CLI / ライブラリ。
`jsonschema` 等の外部 pip 依存は使わない。

## 何を検証するか

JSON Schema draft 2020-12 の必要十分なサブセット:

`type` / `required` / `enum` / `const` / `additionalProperties:false` /
`properties` / `$ref`(`#/$defs/...`) / `oneOf` / `pattern` / `items` /
`minItems` / `minLength` / `maxLength` / `minimum` / `maximum` /
`format: date-time`(緩め: RFC3339 風の形だけ見る) / `format: date`(緩め)。

非対応キーワードは「制約なし(無視)」として扱う。検証器を保守的に倒すための
意図的な設計(false negative を避ける)。

## 使い方

```sh
# このパッケージのテスト (stdlib only)
cd tools/workflow_event && PYTHONPATH=src python -m pytest -q

# CLI で examples を検証
PYTHONPATH=src python -m alo_workflow_event validate \
  --schema ../../docs/workflow_model/v0.2/alo_workflow_event_schema_v0.2.json \
  ../../docs/workflow_model/v0.2/alo_workflow_event_examples_v0.2.jsonl
```

`validate` は全件 green なら exit 0、1 件でも失敗で exit 1。`.jsonl` は
1 行 1 イベント、`.json` は単一オブジェクト又は配列を受け付ける。

## レイアウト

```
tools/workflow_event/
  pyproject.toml
  src/alo_workflow_event/
    __init__.py
    __main__.py
    validator.py   # stdlib-only JSON Schema サブセット検証器
    cli.py         # validate サブコマンド
  tests/
    conftest.py
    test_validator.py  # サブセット挙動の単体テスト
    test_examples.py   # examples 全件 green + ネガティブテスト
    test_cli.py        # CLI 終了コード/出力
```
