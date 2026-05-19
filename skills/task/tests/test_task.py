import json


def test_add_defaults(run):
    proc = run("add", "ship feature")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "ship feature"
    assert rec["status"] == "open"
    assert rec["due"] is None
    assert rec["done_at"] is None
    assert rec["log"] == []
    assert rec["reflection"] is None


def test_add_with_due(run):
    proc = run("add", "deadline thing", "--due", "2026-06-30")
    rec = json.loads(proc.stdout.strip())
    assert rec["due"] == "2026-06-30"


def test_add_due_invalid_exits_1(run):
    run("add", "x", "--due", "tomorrow", expect_code=1)


def test_list_jsonl(run):
    run("add", "one")
    run("add", "two")
    proc = run("list")
    assert len(proc.stdout.strip().splitlines()) == 2


def test_list_status_filter(run):
    run("add", "open thing")
    run("add", "another open")
    proc = run("list", "--status", "open")
    assert len(proc.stdout.strip().splitlines()) == 2


def test_list_status_invalid_exits_1(run):
    run("list", "--status", "bogus", expect_code=1)


def test_list_tsv_header(run):
    run("add", "x", "--tag", "t", "--due", "2026-06-01")
    proc = run("list", "--tsv")
    header = proc.stdout.strip().splitlines()[0].split("\t")
    assert header == ["id", "raw", "status", "due", "tags", "created_at"]


def test_list_due_before_filters(run):
    run("add", "a", "--due", "2026-05-25")
    run("add", "b", "--due", "2026-06-10")
    proc = run("list", "--due-before", "2026-06-01")
    assert "a" in proc.stdout and "b" not in proc.stdout
