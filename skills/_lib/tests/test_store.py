from pathlib import Path

import pytest

import store


def test_aha_home_uses_env_var(aha_home):
    assert store.aha_home() == aha_home


def test_aha_home_defaults_to_home_aha(monkeypatch, tmp_path):
    monkeypatch.delenv("AHA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert store.aha_home() == tmp_path / "aha"


def test_jsonl_path_per_skill(aha_home):
    assert store.jsonl_path("idea") == aha_home / "idea.jsonl"
    assert store.jsonl_path("task") == aha_home / "task.jsonl"


def test_jsonl_path_rejects_unknown_skill(aha_home):
    with pytest.raises(ValueError):
        store.jsonl_path("bogus")


import re
from datetime import datetime


def test_new_id_format():
    rid = store.new_id()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}-[0-9a-f]{4}", rid), rid


def test_new_id_starts_with_today():
    today = datetime.now().strftime("%Y-%m-%d")
    assert store.new_id().startswith(today)


def test_new_id_unique_in_practice():
    ids = {store.new_id() for _ in range(200)}
    assert len(ids) > 190  # collisions extremely rare in 65k space


def test_now_iso_has_offset():
    s = store.now_iso()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)", s), s


def test_exception_hierarchy():
    assert issubclass(store.IdNotFound, store.AhaError)
    assert issubclass(store.CorruptRecord, store.AhaError)


def test_corrupt_record_carries_location():
    err = store.CorruptRecord(path="/tmp/x.jsonl", line_no=3, reason="bad json")
    assert err.path == "/tmp/x.jsonl"
    assert err.line_no == 3
    assert "line 3" in str(err)


def test_ensure_initialized_creates_dir_and_file(aha_home):
    p = aha_home / "idea.jsonl"
    assert not p.exists()
    store.ensure_initialized("idea")
    assert p.exists()
    assert p.read_text() == ""


def test_ensure_initialized_idempotent(aha_home):
    store.ensure_initialized("dao")
    (aha_home / "dao.jsonl").write_text('{"id":"x"}\n')
    store.ensure_initialized("dao")
    assert (aha_home / "dao.jsonl").read_text() == '{"id":"x"}\n'


def test_read_all_empty_when_no_file(aha_home):
    assert store.read_all("idea") == []


def test_read_all_parses_each_line(aha_home):
    p = aha_home / "idea.jsonl"
    p.write_text('{"id":"a","raw":"first"}\n{"id":"b","raw":"second"}\n')
    rows = store.read_all("idea")
    assert [r["id"] for r in rows] == ["a", "b"]


def test_read_all_skips_blank_lines(aha_home):
    p = aha_home / "idea.jsonl"
    p.write_text('{"id":"a"}\n\n{"id":"b"}\n')
    assert [r["id"] for r in store.read_all("idea")] == ["a", "b"]


def test_read_all_raises_corrupt_with_line_no(aha_home):
    p = aha_home / "idea.jsonl"
    p.write_text('{"id":"a"}\nnot-json\n{"id":"c"}\n')
    with pytest.raises(store.CorruptRecord) as ei:
        store.read_all("idea")
    assert ei.value.line_no == 2
