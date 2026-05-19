import json


def test_add_emits_record(run, aha_home):
    proc = run("add", "原话很重要", "--tag", "认知")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "原话很重要"
    assert rec["tags"] == ["认知"]
    assert rec["refined"] is None
    assert rec["refinement_log"] == []
    assert rec["log"] == []
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


def test_refine_archives_previous(run):
    rid = json.loads(run("add", "原话").stdout)["id"]
    run("refine", rid, "v1")
    proc = run("refine", rid, "v2")
    rec = json.loads(proc.stdout.strip())
    assert rec["refined"] == "v2"
    assert rec["raw"] == "原话"
    assert rec["refinement_log"][-1]["prev_refined"] == "v1"


def test_refine_unknown_id(run):
    run("refine", "missing", "x", expect_code=1)


def test_log_appends_note(run):
    rid = json.loads(run("add", "深谈我").stdout)["id"]
    proc = run("log", rid, "本轮:意义溯源\n焦点:边界澄清\n下一步:问反例")
    rec = json.loads(proc.stdout.strip())
    assert len(rec["log"]) == 1
    entry = rec["log"][0]
    assert entry["note"] == "本轮:意义溯源\n焦点:边界澄清\n下一步:问反例"
    assert entry["at"]


def test_log_multiple_appends_in_order(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    run("log", rid, "first")
    run("log", rid, "second")
    proc = run("log", rid, "third")
    rec = json.loads(proc.stdout.strip())
    notes = [e["note"] for e in rec["log"]]
    assert notes == ["first", "second", "third"]
    ats = [e["at"] for e in rec["log"]]
    assert ats == sorted(ats)


def test_log_unknown_id_exits_1(run):
    proc = run("log", "missing-id", "note", expect_code=1)
    assert "not found" in proc.stderr


def test_log_empty_note_exits_1(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("log", rid, "", expect_code=1)
    assert "empty" in proc.stderr.lower() or "must not be empty" in proc.stderr.lower()


def test_log_preserves_other_fields(run):
    rid = json.loads(run("add", "原话", "--tag", "认知").stdout)["id"]
    run("refine", rid, "提炼")
    proc = run("log", rid, "trail note")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "原话"
    assert rec["refined"] == "提炼"
    assert rec["refinement_log"] == []
    assert rec["tags"] == ["认知"]
    assert len(rec["log"]) == 1
    assert rec["log"][0]["note"] == "trail note"
