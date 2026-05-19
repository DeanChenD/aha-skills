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
    assert rec["log"] == []
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


def test_list_empty_produces_no_output(run):
    proc = run("list")
    assert proc.stdout == ""


def test_list_returns_jsonl_lines(run):
    run("add", "one")
    run("add", "two")
    proc = run("list")
    lines = proc.stdout.strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        json.loads(line)


def test_list_filters_by_tag(run):
    run("add", "x-only", "--tag", "x")
    run("add", "y-only", "--tag", "y")
    proc = run("list", "--tag", "x")
    assert len(proc.stdout.strip().splitlines()) == 1
    assert "x-only" in proc.stdout


def test_list_tsv_has_six_columns(run):
    run("add", "raw text", "--status", "incubating", "--tag", "t1")
    proc = run("list", "--tsv")
    rows = proc.stdout.strip().splitlines()
    assert len(rows) == 2
    header = rows[0].split("\t")
    assert header == ["id", "raw", "refined", "status", "tags", "created_at"]
    body = rows[1].split("\t")
    assert body[1] == "raw text"
    assert body[3] == "incubating"
    assert body[4] == "t1"


def test_list_status_filter(run):
    run("add", "open one", "--status", "incubating")
    run("add", "decided one", "--status", "decided")
    proc = run("list", "--status", "decided")
    assert len(proc.stdout.strip().splitlines()) == 1
    assert "decided one" in proc.stdout


def test_refine_sets_refined(run):
    add_proc = run("add", "rough idea")
    rid = json.loads(add_proc.stdout)["id"]
    proc = run("refine", rid, "polished thought")
    rec = json.loads(proc.stdout.strip())
    assert rec["refined"] == "polished thought"
    assert rec["refinement_log"] == []
    assert rec["raw"] == "rough idea"


def test_refine_archives_previous(run):
    rid = json.loads(run("add", "rough").stdout)["id"]
    run("refine", rid, "v1")
    proc = run("refine", rid, "v2")
    rec = json.loads(proc.stdout.strip())
    assert rec["refined"] == "v2"
    assert len(rec["refinement_log"]) == 1
    assert rec["refinement_log"][0]["prev_refined"] == "v1"


def test_refine_unknown_id_exits_1(run):
    proc = run("refine", "missing-id", "x", expect_code=1)
    assert "not found" in proc.stderr


def test_set_status_updates(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("set-status", rid, "decided")
    rec = json.loads(proc.stdout.strip())
    assert rec["status"] == "decided"


def test_set_status_unknown_id_exits_1(run):
    run("set-status", "missing-id", "decided", expect_code=1)


def test_log_appends_note(run):
    rid = json.loads(run("add", "discuss me").stdout)["id"]
    proc = run("log", rid, "本轮:澄清目标用户\n焦点:替代方案\n下一步:问现在怎么解决")
    rec = json.loads(proc.stdout.strip())
    assert len(rec["log"]) == 1
    entry = rec["log"][0]
    assert entry["note"] == "本轮:澄清目标用户\n焦点:替代方案\n下一步:问现在怎么解决"
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
    rid = json.loads(run("add", "rough", "--tag", "t1").stdout)["id"]
    run("refine", rid, "polished")
    proc = run("log", rid, "trail note")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "rough"
    assert rec["refined"] == "polished"
    assert rec["refinement_log"] == []
    assert rec["tags"] == ["t1"]
    assert len(rec["log"]) == 1
    assert rec["log"][0]["note"] == "trail note"
