import json


def test_add_emits_record(run, aha_home):
    proc = run("add", "原话很重要", "--tag", "认知")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "原话很重要"
    assert rec["tags"] == ["认知"]
    assert rec["refined"] is None
    assert rec["refinement_log"] == []
    assert "status" not in rec


def test_add_writes_utf8_no_escape(run, aha_home):
    run("add", "中文内容")
    contents = (aha_home / "dao.jsonl").read_text(encoding="utf-8")
    assert "中文内容" in contents
    assert "\\u" not in contents


def test_list_jsonl(run):
    run("add", "one")
    run("add", "two")
    proc = run("list")
    lines = proc.stdout.strip().splitlines()
    assert len(lines) == 2
    for l in lines:
        json.loads(l)


def test_list_tsv_columns(run):
    run("add", "raw", "--tag", "t1")
    proc = run("list", "--tsv")
    rows = proc.stdout.strip().splitlines()
    assert rows[0].split("\t") == ["id", "raw", "refined", "tags", "created_at"]


def test_list_tag_filter(run):
    run("add", "alpha", "--tag", "a")
    run("add", "beta", "--tag", "b")
    proc = run("list", "--tag", "a")
    assert "alpha" in proc.stdout
    assert "beta" not in proc.stdout
