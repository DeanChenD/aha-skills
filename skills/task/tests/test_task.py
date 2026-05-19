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
