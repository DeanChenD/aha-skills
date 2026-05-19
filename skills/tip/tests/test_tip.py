import json


def test_add_minimal(run, aha_home):
    proc = run("add", "用 grep 而不是 search")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "用 grep 而不是 search"
    assert rec["tags"] == []
    assert "refined" not in rec
    assert "status" not in rec
    assert rec["id"]


def test_add_with_tags(run):
    proc = run("add", "shortcut", "--tag", "cli", "--tag", "vim")
    rec = json.loads(proc.stdout.strip())
    assert rec["tags"] == ["cli", "vim"]
