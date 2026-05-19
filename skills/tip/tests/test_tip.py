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


def test_list_jsonl(run):
    run("add", "one")
    run("add", "two")
    proc = run("list")
    assert len(proc.stdout.strip().splitlines()) == 2


def test_list_tsv_header(run):
    run("add", "x", "--tag", "t")
    proc = run("list", "--tsv")
    rows = proc.stdout.strip().splitlines()
    assert rows[0].split("\t") == ["id", "raw", "tags", "created_at"]


def test_list_tag_filter(run):
    run("add", "vim", "--tag", "vim")
    run("add", "git", "--tag", "git")
    proc = run("list", "--tag", "vim")
    assert "vim" in proc.stdout and "git" not in proc.stdout
