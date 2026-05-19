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
