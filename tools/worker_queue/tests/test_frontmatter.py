from alo_worker.frontmatter import as_list, split_frontmatter


def test_scalars_and_inline_comment():
    text = "---\nworker_task_id: W-1   # P0\nstatus: queued\n---\nbody\n"
    meta, body = split_frontmatter(text)
    assert meta["worker_task_id"] == "W-1"
    assert meta["status"] == "queued"
    assert body.strip() == "body"


def test_value_with_colon_kept():
    meta, _ = split_frontmatter("---\ntest_command: pytest tests/xdoc -q\n---\n")
    assert meta["test_command"] == "pytest tests/xdoc -q"


def test_block_list_parsed():
    text = (
        "---\n"
        "allowed_paths:\n"
        "  - src/xdoc/\n"
        "  - tests/xdoc/   # inline ok\n"
        "forbidden_actions:\n"
        "  - schema_migration\n"
        "next: scalar\n"
        "---\n"
    )
    meta, _ = split_frontmatter(text)
    assert meta["allowed_paths"] == ["src/xdoc/", "tests/xdoc/"]
    assert meta["forbidden_actions"] == ["schema_migration"]
    assert meta["next"] == "scalar"


def test_nested_map_is_skipped_not_crash():
    text = (
        "---\n"
        "target:\n"
        "  repo: ALOBookDX\n"
        "  files:\n"
        "    - a.md\n"
        "goal: do it\n"
        "---\n"
    )
    meta, _ = split_frontmatter(text)
    # nested map は無視されるが goal は拾える
    assert meta["goal"] == "do it"


def test_no_frontmatter():
    meta, body = split_frontmatter("just text\n")
    assert meta == {}
    assert body == "just text\n"


def test_as_list_normalizes():
    assert as_list("x") == ["x"]
    assert as_list(["a", "b"]) == ["a", "b"]
    assert as_list("") == []
