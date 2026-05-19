import json


def test_no_args_exits_1(run):
    proc = run(expect_code=1)
    assert "Error:" in proc.stderr or "usage" in proc.stderr.lower()


def test_unknown_verb_exits_1(run):
    run("frobnicate", expect_code=1)


def test_add_emits_full_record(run, aha_home):
    proc = run("add", "first idea", "--tag", "x", "--tag", "y")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "first idea"
    assert rec["tags"] == ["x", "y"]
    assert rec["status"] is None
    assert rec["refined"] is None
    assert rec["refinement_log"] == []
    assert rec["id"]
    assert rec["created_at"]
    assert rec["updated_at"] == rec["created_at"]


def test_add_with_status(run):
    proc = run("add", "starts with status", "--status", "incubating")
    rec = json.loads(proc.stdout.strip())
    assert rec["status"] == "incubating"


def test_add_persists_to_jsonl(run, aha_home):
    run("add", "persisted")
    contents = (aha_home / "idea.jsonl").read_text()
    assert "persisted" in contents
    json.loads(contents.strip())
