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
