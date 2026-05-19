# aha-skills Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild aha-skills from scratch around JSONL-as-source-of-truth, replacing ~4000 LOC of Markdown-management Python with a small (≤1050 prod LOC) lib + 4 CLI scripts + 5 SKILL.md files.

**Architecture:** Single shared lib (`skills/_lib/store.py`) provides JSONL CRUD + locking + id/timestamp helpers + an argparse subclass. Four per-skill CLIs (`skills/<skill>/scripts/<skill>.py`) compose those primitives into 15 verbs total. A fifth skill (`reflect`) is SKILL.md only — agent-driven, no script. Data lives in `~/aha/{idea,dao,tip,task}.jsonl`, one record per line, append/rewrite under `fcntl.flock` with atomic temp+rename.

**Tech Stack:** Python 3.11+ (stdlib only: `json`, `pathlib`, `os`, `secrets`, `datetime`, `fcntl`, `argparse`, `sys`, `contextlib`). Pytest as the only dev dependency. macOS/Linux only (Windows is YAGNI).

**Source spec:** `docs/superpowers/specs/2026-05-19-aha-skills-redesign-design.md`

---

## Phase 0: Cleanup

### Task 0.1: Delete old implementation

**Files:**
- Delete: `skills/_lib/`, `skills/idea/`, `skills/dao/`, `skills/daily/`, `skills/reflect/`, `scripts/`, `aha-workspace/`, `docs/audit-backlog-2026-05-15.md`, `README.md`, `README.en.md`, `Makefile`

- [ ] **Step 1: Verify what's about to be removed**

Run: `git status && ls skills scripts aha-workspace 2>&1`
Expected: clean tree with the directories above present.

- [ ] **Step 2: Remove old artifacts**

```bash
git rm -rf skills/_lib skills/idea skills/dao skills/daily skills/reflect scripts aha-workspace docs/audit-backlog-2026-05-15.md README.md README.en.md Makefile
```

- [ ] **Step 3: Commit cleanup**

```bash
git add -A
git commit -m "chore: remove markdown-era implementation before JSONL redesign

Delete skills/_lib (markdown library), all skill directories, scripts/,
aha-workspace/, audit doc, README files, and Makefile. Spec at
docs/superpowers/specs/2026-05-19-aha-skills-redesign-design.md drives
the rebuild."
```

- [ ] **Step 4: Verify clean slate**

Run: `find skills -type f 2>/dev/null; ls aha-workspace 2>&1`
Expected: nothing under `skills/`; `aha-workspace` "No such file or directory".

---

## Phase 1: store.py — shared library

> All Phase 1 tasks live under `skills/_lib/`. Tests run via `pytest skills/_lib/tests/ -v`.

### Task 1.1: Project skeleton + path resolution

**Files:**
- Create: `skills/_lib/store.py`
- Create: `skills/_lib/__init__.py`
- Create: `skills/_lib/tests/__init__.py`
- Create: `skills/_lib/tests/conftest.py`
- Create: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests for paths**

Create `skills/_lib/tests/conftest.py`:
```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def aha_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AHA_HOME", str(tmp_path))
    return tmp_path
```

Create `skills/_lib/tests/test_store.py`:
```python
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
```

Create empty `skills/_lib/__init__.py` and `skills/_lib/tests/__init__.py`.

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest skills/_lib/tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'store'`.

- [ ] **Step 3: Implement paths**

Create `skills/_lib/store.py`:
```python
"""aha-skills shared store: JSONL CRUD, ids, timestamps, locking."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

Skill = Literal["idea", "dao", "tip", "task"]
SKILLS: tuple[Skill, ...] = ("idea", "dao", "tip", "task")


def aha_home() -> Path:
    if env := os.environ.get("AHA_HOME"):
        return Path(env).expanduser().resolve()
    try:
        return (Path.home() / "aha").resolve()
    except RuntimeError as e:
        raise RuntimeError(
            "Could not determine home directory. Set AHA_HOME."
        ) from e


def jsonl_path(skill: str) -> Path:
    if skill not in SKILLS:
        raise ValueError(f"unknown skill: {skill!r} (expected one of {SKILLS})")
    return aha_home() / f"{skill}.jsonl"
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest skills/_lib/tests/test_store.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): path resolution with AHA_HOME override"
```

### Task 1.2: id generation and ISO timestamps

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `skills/_lib/tests/test_store.py`:
```python
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k "new_id or now_iso"`
Expected: FAIL — `AttributeError: module 'store' has no attribute 'new_id'`.

- [ ] **Step 3: Implement**

Add to `skills/_lib/store.py`:
```python
import secrets
from datetime import datetime


def new_id() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{today}-{secrets.token_hex(2)}"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k "new_id or now_iso"`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): new_id and now_iso helpers"
```

### Task 1.3: Exceptions

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing test**

Append to `skills/_lib/tests/test_store.py`:
```python
def test_exception_hierarchy():
    assert issubclass(store.IdNotFound, store.AhaError)
    assert issubclass(store.CorruptRecord, store.AhaError)


def test_corrupt_record_carries_location():
    err = store.CorruptRecord(path="/tmp/x.jsonl", line_no=3, reason="bad json")
    assert err.path == "/tmp/x.jsonl"
    assert err.line_no == 3
    assert "line 3" in str(err)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py::test_exception_hierarchy -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `skills/_lib/store.py`:
```python
class AhaError(Exception):
    """Base class for aha-skills errors."""


class IdNotFound(AhaError):
    def __init__(self, skill: str, id: str):
        super().__init__(f"id {id!r} not found in {skill}")
        self.skill = skill
        self.id = id


class CorruptRecord(AhaError):
    def __init__(self, path: str, line_no: int, reason: str):
        super().__init__(f"{path} line {line_no}: {reason}")
        self.path = path
        self.line_no = line_no
        self.reason = reason
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k "exception or corrupt"`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): error hierarchy with line-located CorruptRecord"
```

### Task 1.4: ensure_initialized (lazy mkdir + touch)

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing test**

Append to `test_store.py`:
```python
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k ensure_initialized`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
def ensure_initialized(skill: str) -> None:
    p = jsonl_path(skill)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.touch()
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k ensure_initialized`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): lazy ensure_initialized"
```

### Task 1.5: read_all + corruption detection

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `test_store.py`:
```python
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k read_all`
Expected: FAIL — `read_all` undefined.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
import json


def read_all(skill: str) -> list[dict]:
    p = jsonl_path(skill)
    if not p.exists():
        return []
    out: list[dict] = []
    with p.open() as f:
        for i, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                out.append(json.loads(stripped))
            except json.JSONDecodeError as e:
                raise CorruptRecord(str(p), i, str(e)) from e
    return out
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k read_all`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): read_all with line-located corruption errors"
```

### Task 1.6: find_by_id

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `test_store.py`:
```python
def test_find_by_id_hit(aha_home):
    (aha_home / "idea.jsonl").write_text('{"id":"a"}\n{"id":"b"}\n')
    assert store.find_by_id("idea", "b") == {"id": "b"}


def test_find_by_id_miss_returns_none(aha_home):
    (aha_home / "idea.jsonl").write_text('{"id":"a"}\n')
    assert store.find_by_id("idea", "z") is None
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k find_by_id`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
def find_by_id(skill: str, id: str) -> dict | None:
    for rec in read_all(skill):
        if rec.get("id") == id:
            return rec
    return None
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k find_by_id`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): find_by_id"
```

### Task 1.7: filter_records

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `test_store.py`:
```python
SAMPLE = [
    {"id": "a", "tags": ["x"], "status": "open",
     "created_at": "2026-05-10T12:00:00+08:00", "due": "2026-05-20"},
    {"id": "b", "tags": ["x", "y"], "status": "done",
     "created_at": "2026-05-15T12:00:00+08:00", "due": "2026-05-12"},
    {"id": "c", "tags": ["y"], "status": "open",
     "created_at": "2026-05-18T12:00:00+08:00", "due": None},
]


def test_filter_by_tag_any():
    out = store.filter_records(SAMPLE, tags=["x"])
    assert [r["id"] for r in out] == ["a", "b"]


def test_filter_by_multiple_tags_is_or():
    out = store.filter_records(SAMPLE, tags=["x", "y"])
    assert [r["id"] for r in out] == ["a", "b", "c"]


def test_filter_by_since():
    out = store.filter_records(SAMPLE, since="2026-05-15")
    assert [r["id"] for r in out] == ["b", "c"]


def test_filter_by_until_inclusive():
    out = store.filter_records(SAMPLE, until="2026-05-15")
    assert [r["id"] for r in out] == ["a", "b"]


def test_filter_by_status():
    out = store.filter_records(SAMPLE, status="open")
    assert [r["id"] for r in out] == ["a", "c"]


def test_filter_by_due_before_skips_null():
    out = store.filter_records(SAMPLE, due_before="2026-05-19")
    assert [r["id"] for r in out] == ["b"]


def test_filter_limit_keeps_first_n():
    out = store.filter_records(SAMPLE, limit=2)
    assert [r["id"] for r in out] == ["a", "b"]
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k filter`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
def filter_records(
    records: list[dict],
    *,
    since: str | None = None,
    until: str | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
    due_before: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    out = list(records)
    if since:
        out = [r for r in out if r.get("created_at", "") >= since]
    if until:
        out = [r for r in out if r.get("created_at", "")[:10] <= until]
    if tags:
        wanted = set(tags)
        out = [r for r in out if wanted & set(r.get("tags") or [])]
    if status:
        out = [r for r in out if r.get("status") == status]
    if due_before:
        out = [r for r in out if r.get("due") and r["due"] < due_before]
    if limit is not None:
        out = out[:limit]
    return out
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k filter`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): filter_records (since/until/tags/status/due_before/limit)"
```

### Task 1.8: to_jsonl_line + to_tsv_row

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `test_store.py`:
```python
def test_to_jsonl_line_no_unicode_escape():
    line = store.to_jsonl_line({"raw": "你好"})
    assert "你好" in line
    assert "\\u" not in line
    assert line.endswith("}")
    assert "\n" not in line


def test_to_tsv_row_pads_missing_with_dash():
    row = store.to_tsv_row({"id": "a"}, ["id", "raw", "status"])
    assert row.split("\t") == ["a", "-", "-"]


def test_to_tsv_row_truncates_long_text():
    long = "x" * 100
    row = store.to_tsv_row({"raw": long}, ["raw"])
    cell = row.split("\t")[0]
    assert cell.endswith("…")
    assert len(cell) == 61  # 60 chars + ellipsis


def test_to_tsv_row_joins_tag_list():
    row = store.to_tsv_row({"tags": ["x", "y"]}, ["tags"])
    assert row == "x,y"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k "jsonl_line or tsv_row"`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
TSV_TRUNC = 60


def to_jsonl_line(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"))


def to_tsv_row(record: dict, columns: list[str]) -> str:
    cells: list[str] = []
    for col in columns:
        v = record.get(col)
        if v is None or v == "" or v == []:
            cells.append("-")
            continue
        if isinstance(v, list):
            cells.append(",".join(str(x) for x in v))
            continue
        s = str(v).replace("\t", " ").replace("\n", " ")
        if len(s) > TSV_TRUNC:
            s = s[:TSV_TRUNC] + "…"
        cells.append(s)
    return "\t".join(cells)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k "jsonl_line or tsv_row"`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): to_jsonl_line (utf8) and to_tsv_row (truncate+pad)"
```

### Task 1.9: locked() + atomic write

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing test**

Append to `test_store.py`:
```python
def test_atomic_write_replaces_file(aha_home):
    p = aha_home / "idea.jsonl"
    p.write_text("old\n")
    store._atomic_write_lines(p, ['{"id":"a"}', '{"id":"b"}'])
    assert p.read_text() == '{"id":"a"}\n{"id":"b"}\n'


def test_atomic_write_handles_empty(aha_home):
    p = aha_home / "idea.jsonl"
    store._atomic_write_lines(p, [])
    assert p.read_text() == ""


def test_locked_creates_file_if_missing(aha_home):
    p = aha_home / "idea.jsonl"
    with store.locked(p):
        pass
    assert p.exists()
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k "atomic_write or locked"`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
import fcntl
from contextlib import contextmanager


@contextmanager
def locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    with open(path, "r+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _atomic_write_lines(path: Path, lines: list[str]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    body = "\n".join(lines) + ("\n" if lines else "")
    with open(tmp, "w") as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k "atomic_write or locked"`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): locked() context + _atomic_write_lines"
```

### Task 1.10: append_record

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `test_store.py`:
```python
def test_append_record_writes_one_line(aha_home):
    rec = {"id": "x", "raw": "hi"}
    store.append_record("idea", rec)
    contents = (aha_home / "idea.jsonl").read_text()
    assert contents == '{"id":"x","raw":"hi"}\n'


def test_append_record_appends_multiple(aha_home):
    store.append_record("idea", {"id": "a"})
    store.append_record("idea", {"id": "b"})
    assert (aha_home / "idea.jsonl").read_text() == '{"id":"a"}\n{"id":"b"}\n'
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k append_record`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
def append_record(skill: str, record: dict) -> None:
    p = jsonl_path(skill)
    line = to_jsonl_line(record) + "\n"
    with locked(p) as f:
        f.seek(0, os.SEEK_END)
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k append_record`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): append_record under flock"
```

### Task 1.11: update_record

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `test_store.py`:
```python
def test_update_record_applies_mutator(aha_home):
    (aha_home / "idea.jsonl").write_text('{"id":"a","status":null}\n')
    out = store.update_record("idea", "a", lambda r: {**r, "status": "decided"})
    assert out["status"] == "decided"
    assert (aha_home / "idea.jsonl").read_text().strip() == '{"id":"a","status":"decided"}'


def test_update_record_missing_raises(aha_home):
    (aha_home / "idea.jsonl").write_text('{"id":"a"}\n')
    with pytest.raises(store.IdNotFound):
        store.update_record("idea", "missing", lambda r: r)


def test_update_record_bumps_updated_at(aha_home):
    (aha_home / "idea.jsonl").write_text(
        '{"id":"a","updated_at":"2020-01-01T00:00:00+00:00"}\n'
    )
    out = store.update_record("idea", "a", lambda r: {**r, "tags": ["t"]})
    assert out["updated_at"] != "2020-01-01T00:00:00+00:00"


def test_update_record_preserves_other_lines(aha_home):
    (aha_home / "idea.jsonl").write_text('{"id":"a"}\n{"id":"b"}\n{"id":"c"}\n')
    store.update_record("idea", "b", lambda r: {**r, "status": "X"})
    lines = (aha_home / "idea.jsonl").read_text().splitlines()
    assert lines[0] == '{"id":"a"}'
    assert lines[2] == '{"id":"c"}'
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k update_record`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
from typing import Callable


def update_record(
    skill: str, id: str, mutator: Callable[[dict], dict]
) -> dict:
    p = jsonl_path(skill)
    with locked(p) as f:
        f.seek(0)
        raw = f.read()
        records: list[dict] = []
        for i, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise CorruptRecord(str(p), i, str(e)) from e
        for idx, rec in enumerate(records):
            if rec.get("id") == id:
                new_rec = mutator(rec)
                new_rec["updated_at"] = now_iso()
                records[idx] = new_rec
                _atomic_write_lines(p, [to_jsonl_line(r) for r in records])
                return new_rec
        raise IdNotFound(skill, id)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k update_record`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): update_record with mutator + updated_at bump"
```

### Task 1.12: refine_record (raw immutability + log archive)

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `test_store.py`:
```python
def test_refine_first_time_no_log_entry(aha_home):
    (aha_home / "idea.jsonl").write_text(
        '{"id":"a","raw":"orig","refined":null,"refinement_log":[]}\n'
    )
    out = store.refine_record("idea", "a", "v1")
    assert out["refined"] == "v1"
    assert out["refinement_log"] == []
    assert out["raw"] == "orig"


def test_refine_archives_previous(aha_home):
    (aha_home / "idea.jsonl").write_text(
        '{"id":"a","raw":"orig","refined":"v1","refinement_log":[]}\n'
    )
    out = store.refine_record("idea", "a", "v2")
    assert out["refined"] == "v2"
    assert len(out["refinement_log"]) == 1
    assert out["refinement_log"][0]["prev_refined"] == "v1"
    assert "at" in out["refinement_log"][0]


def test_refine_does_not_mutate_raw(aha_home):
    (aha_home / "idea.jsonl").write_text(
        '{"id":"a","raw":"orig","refined":null,"refinement_log":[]}\n'
    )
    out = store.refine_record("idea", "a", "v1")
    assert out["raw"] == "orig"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k refine`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
def refine_record(skill: str, id: str, new_refined: str) -> dict:
    def mutate(rec: dict) -> dict:
        out = dict(rec)
        log = list(out.get("refinement_log") or [])
        prev = out.get("refined")
        if prev is not None:
            log.append({"at": now_iso(), "prev_refined": prev})
        out["refined"] = new_refined
        out["refinement_log"] = log
        return out

    return update_record(skill, id, mutate)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k refine`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): refine_record archives prior refined into log"
```

### Task 1.13: append_log (task only, append-only)

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `test_store.py`:
```python
def test_append_log_appends(aha_home):
    (aha_home / "task.jsonl").write_text(
        '{"id":"a","log":[]}\n'
    )
    out = store.append_log("task", "a", "first note")
    assert out["log"][-1]["note"] == "first note"
    assert "at" in out["log"][-1]


def test_append_log_preserves_existing(aha_home):
    (aha_home / "task.jsonl").write_text(
        '{"id":"a","log":[{"at":"2026-01-01T00:00:00+00:00","note":"n0"}]}\n'
    )
    out = store.append_log("task", "a", "n1")
    assert [e["note"] for e in out["log"]] == ["n0", "n1"]
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k append_log`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
def append_log(skill: str, id: str, note: str) -> dict:
    def mutate(rec: dict) -> dict:
        out = dict(rec)
        log = list(out.get("log") or [])
        log.append({"at": now_iso(), "note": note})
        out["log"] = log
        return out

    return update_record(skill, id, mutate)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k append_log`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): append_log for task progress notes"
```

### Task 1.14: mark_done + mark_dropped

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing tests**

Append to `test_store.py`:
```python
def test_mark_done_sets_status_and_done_at(aha_home):
    (aha_home / "task.jsonl").write_text('{"id":"a","status":"open","done_at":null}\n')
    out = store.mark_done("task", "a")
    assert out["status"] == "done"
    assert out["done_at"]


def test_mark_done_with_reflection(aha_home):
    (aha_home / "task.jsonl").write_text(
        '{"id":"a","status":"open","done_at":null,"reflection":null}\n'
    )
    out = store.mark_done("task", "a", reflection="went well")
    assert out["reflection"] == "went well"


def test_mark_dropped_sets_status_dropped(aha_home):
    (aha_home / "task.jsonl").write_text('{"id":"a","status":"open","done_at":null}\n')
    out = store.mark_dropped("task", "a")
    assert out["status"] == "dropped"
    assert out["done_at"]


def test_mark_dropped_keeps_reflection_optional(aha_home):
    (aha_home / "task.jsonl").write_text(
        '{"id":"a","status":"open","done_at":null,"reflection":null}\n'
    )
    out = store.mark_dropped("task", "a")
    assert out["reflection"] is None
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k "mark_done or mark_dropped"`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
def _mark(skill: str, id: str, status: str, reflection: str | None) -> dict:
    def mutate(rec: dict) -> dict:
        out = dict(rec)
        out["status"] = status
        out["done_at"] = now_iso()
        if reflection is not None:
            out["reflection"] = reflection
        return out

    return update_record(skill, id, mutate)


def mark_done(skill: str, id: str, reflection: str | None = None) -> dict:
    return _mark(skill, id, "done", reflection)


def mark_dropped(skill: str, id: str, reflection: str | None = None) -> dict:
    return _mark(skill, id, "dropped", reflection)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k "mark_done or mark_dropped"`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): mark_done/mark_dropped set status+done_at atomically"
```

### Task 1.15: AhaArgParser

**Files:**
- Modify: `skills/_lib/store.py`
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write failing test**

Append to `test_store.py`:
```python
import argparse


def test_aha_argparser_exits_1_on_error(capsys):
    p = store.AhaArgParser()
    p.add_argument("--n", type=int)
    with pytest.raises(SystemExit) as ei:
        p.parse_args(["--n", "abc"])
    assert ei.value.code == 1
    err = capsys.readouterr().err
    assert "Error:" in err


def test_aha_argparser_extends_argparse():
    assert issubclass(store.AhaArgParser, argparse.ArgumentParser)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/_lib/tests/test_store.py -v -k aha_argparser`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `store.py`:
```python
import argparse
import sys


class AhaArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        sys.stderr.write(f"Error: {message}\n")
        self.print_usage(sys.stderr)
        sys.exit(1)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/_lib/tests/test_store.py -v -k aha_argparser`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib
git commit -m "feat(store): AhaArgParser overrides argparse exit code to 1"
```

### Task 1.16: Concurrency tests

**Files:**
- Modify: `skills/_lib/tests/test_store.py`

- [ ] **Step 1: Write tests for concurrent appends and updates**

Append to `test_store.py`:
```python
import threading


def test_concurrent_appends_no_loss(aha_home):
    N = 20
    barrier = threading.Barrier(N)

    def worker(i):
        barrier.wait()
        store.append_record("idea", {"id": f"id-{i}", "raw": f"r{i}"})

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()

    rows = store.read_all("idea")
    assert len(rows) == N
    assert {r["id"] for r in rows} == {f"id-{i}" for i in range(N)}


def test_concurrent_updates_no_overwrite(aha_home):
    (aha_home / "task.jsonl").write_text('{"id":"a","log":[]}\n')
    N = 10
    barrier = threading.Barrier(N)

    def worker(i):
        barrier.wait()
        store.append_log("task", "a", f"note-{i}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()

    rec = store.find_by_id("task", "a")
    assert len(rec["log"]) == N
    assert {e["note"] for e in rec["log"]} == {f"note-{i}" for i in range(N)}
```

- [ ] **Step 2: Run — expect PASS (lock already implemented)**

Run: `pytest skills/_lib/tests/test_store.py -v -k concurrent`
Expected: 2 passed.

- [ ] **Step 3: Run full store suite**

Run: `pytest skills/_lib/tests/ -v`
Expected: ~40 passed.

- [ ] **Step 4: Commit**

```bash
git add skills/_lib
git commit -m "test(store): concurrent append and update integrity"
```

---

## Phase 2: idea CLI

> All Phase 2 tasks live under `skills/idea/`. Tests run via `pytest skills/idea/tests/ -v`.

### Task 2.1: idea skeleton

**Files:**
- Create: `skills/idea/__init__.py`
- Create: `skills/idea/scripts/__init__.py`
- Create: `skills/idea/scripts/idea.py`
- Create: `skills/idea/tests/__init__.py`
- Create: `skills/idea/tests/conftest.py`
- Create: `skills/idea/tests/test_idea.py`

- [ ] **Step 1: Write failing test for help/error handling**

Create `skills/idea/tests/conftest.py`:
```python
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "idea.py"


@pytest.fixture
def aha_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AHA_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def run(aha_home):
    def _run(*args, expect_code: int = 0):
        env = {**os.environ, "AHA_HOME": str(aha_home)}
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == expect_code, (
            f"exit={proc.returncode} expected={expect_code}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
        return proc
    return _run
```

Create `skills/idea/tests/test_idea.py`:
```python
def test_no_args_exits_1(run):
    proc = run(expect_code=1)
    assert "Error:" in proc.stderr or "usage" in proc.stderr.lower()


def test_unknown_verb_exits_1(run):
    proc = run("frobnicate", expect_code=1)
```

Create empty `skills/idea/__init__.py`, `skills/idea/scripts/__init__.py`, `skills/idea/tests/__init__.py`.

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/idea/tests/test_idea.py -v`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Implement skeleton**

Create `skills/idea/scripts/idea.py`:
```python
#!/usr/bin/env python3
"""idea CLI."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
import store  # noqa: E402

SKILL = "idea"


def main() -> None:
    p = store.AhaArgParser(prog="idea")
    sub = p.add_subparsers(dest="cmd", required=True)
    args = p.parse_args()
    try:
        args.fn(args)
    except store.IdNotFound as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except store.CorruptRecord as e:
        print(f"Data error: {e}", file=sys.stderr)
        sys.exit(2)
    except (OSError, RuntimeError) as e:
        print(f"System error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/idea/tests/test_idea.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/idea
git commit -m "feat(idea): CLI skeleton with AhaArgParser dispatch"
```

### Task 2.2: idea add

**Files:**
- Modify: `skills/idea/scripts/idea.py`
- Modify: `skills/idea/tests/test_idea.py`

- [ ] **Step 1: Write failing tests**

Append to `skills/idea/tests/test_idea.py`:
```python
import json


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
    json.loads(contents.strip())  # well-formed
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/idea/tests/test_idea.py -v -k add`
Expected: FAIL — no `add` subcommand.

- [ ] **Step 3: Implement**

In `skills/idea/scripts/idea.py`, replace `main()` body:
```python
def cmd_add(args) -> None:
    rec = {
        "id": store.new_id(),
        "raw": args.raw,
        "tags": args.tag or [],
        "created_at": store.now_iso(),
        "updated_at": "",
        "status": args.status,
        "refined": None,
        "refinement_log": [],
    }
    rec["updated_at"] = rec["created_at"]
    store.ensure_initialized(SKILL)
    store.append_record(SKILL, rec)
    print(store.to_jsonl_line(rec))


def main() -> None:
    p = store.AhaArgParser(prog="idea")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="capture a new idea")
    a.add_argument("raw")
    a.add_argument("--tag", action="append", default=[])
    a.add_argument("--status", default=None)
    a.set_defaults(fn=cmd_add)

    args = p.parse_args()
    try:
        args.fn(args)
    except store.IdNotFound as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except store.CorruptRecord as e:
        print(f"Data error: {e}", file=sys.stderr); sys.exit(2)
    except (OSError, RuntimeError) as e:
        print(f"System error: {e}", file=sys.stderr); sys.exit(2)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/idea/tests/test_idea.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/idea
git commit -m "feat(idea): add verb"
```

### Task 2.3: idea list (default JSONL + --tsv)

**Files:**
- Modify: `skills/idea/scripts/idea.py`
- Modify: `skills/idea/tests/test_idea.py`

- [ ] **Step 1: Write failing tests**

Append to `test_idea.py`:
```python
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
    assert len(rows) == 2  # header + 1
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/idea/tests/test_idea.py -v -k list`
Expected: FAIL — no `list` verb.

- [ ] **Step 3: Implement**

Add to `skills/idea/scripts/idea.py` before `main`:
```python
TSV_COLS = ["id", "raw", "refined", "status", "tags", "created_at"]


def cmd_list(args) -> None:
    records = store.read_all(SKILL)
    records = store.filter_records(
        records,
        since=args.since,
        until=args.until,
        tags=args.tag or None,
        status=args.status,
        limit=args.limit,
    )
    if args.tsv:
        print("\t".join(TSV_COLS))
        for r in records:
            print(store.to_tsv_row(r, TSV_COLS))
    else:
        for r in records:
            print(store.to_jsonl_line(r))
```

In `main()`, register the subparser before `args = p.parse_args()`:
```python
    l = sub.add_parser("list", help="list ideas")
    l.add_argument("--tag", action="append", default=[])
    l.add_argument("--status", default=None)
    l.add_argument("--since", default=None)
    l.add_argument("--until", default=None)
    l.add_argument("--limit", type=int, default=None)
    l.add_argument("--tsv", action="store_true")
    l.set_defaults(fn=cmd_list)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/idea/tests/test_idea.py -v -k list`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/idea
git commit -m "feat(idea): list (jsonl default, --tsv with fixed columns)"
```

### Task 2.4: idea refine

**Files:**
- Modify: `skills/idea/scripts/idea.py`
- Modify: `skills/idea/tests/test_idea.py`

- [ ] **Step 1: Write failing tests**

Append to `test_idea.py`:
```python
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/idea/tests/test_idea.py -v -k refine`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `skills/idea/scripts/idea.py`:
```python
def cmd_refine(args) -> None:
    out = store.refine_record(SKILL, args.id, args.refined)
    print(store.to_jsonl_line(out))
```

Register in `main()`:
```python
    r = sub.add_parser("refine", help="set or update refined wording")
    r.add_argument("id")
    r.add_argument("refined")
    r.set_defaults(fn=cmd_refine)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/idea/tests/test_idea.py -v -k refine`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/idea
git commit -m "feat(idea): refine verb"
```

### Task 2.5: idea set-status

**Files:**
- Modify: `skills/idea/scripts/idea.py`
- Modify: `skills/idea/tests/test_idea.py`

- [ ] **Step 1: Write failing tests**

Append to `test_idea.py`:
```python
def test_set_status_updates(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("set-status", rid, "decided")
    rec = json.loads(proc.stdout.strip())
    assert rec["status"] == "decided"


def test_set_status_unknown_id_exits_1(run):
    run("set-status", "missing-id", "decided", expect_code=1)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/idea/tests/test_idea.py -v -k set_status`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `skills/idea/scripts/idea.py`:
```python
def cmd_set_status(args) -> None:
    out = store.update_record(SKILL, args.id, lambda r: {**r, "status": args.status})
    print(store.to_jsonl_line(out))
```

Register in `main()`:
```python
    s = sub.add_parser("set-status", help="update free-form status")
    s.add_argument("id")
    s.add_argument("status")
    s.set_defaults(fn=cmd_set_status)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/idea/tests/test_idea.py -v`
Expected: all idea tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/idea
git commit -m "feat(idea): set-status verb"
```

---

## Phase 3: dao CLI

> Tests run via `pytest skills/dao/tests/ -v`.

### Task 3.1: dao skeleton + add

**Files:**
- Create: `skills/dao/__init__.py`
- Create: `skills/dao/scripts/__init__.py`
- Create: `skills/dao/scripts/dao.py`
- Create: `skills/dao/tests/__init__.py`
- Create: `skills/dao/tests/conftest.py`
- Create: `skills/dao/tests/test_dao.py`

- [ ] **Step 1: Write failing test**

Create `skills/dao/tests/conftest.py`:
```python
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dao.py"


@pytest.fixture
def aha_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AHA_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def run(aha_home):
    def _run(*args, expect_code: int = 0):
        env = {**os.environ, "AHA_HOME": str(aha_home)}
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == expect_code, (
            f"exit={proc.returncode} expected={expect_code}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
        return proc
    return _run
```

Create `skills/dao/tests/test_dao.py`:
```python
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
```

Create empty `__init__.py` files in `skills/dao/`, `skills/dao/scripts/`, `skills/dao/tests/`.

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/dao/tests/test_dao.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

Create `skills/dao/scripts/dao.py`:
```python
#!/usr/bin/env python3
"""dao CLI."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
import store  # noqa: E402

SKILL = "dao"
TSV_COLS = ["id", "raw", "refined", "tags", "created_at"]


def cmd_add(args) -> None:
    rec = {
        "id": store.new_id(),
        "raw": args.raw,
        "tags": args.tag or [],
        "created_at": store.now_iso(),
        "updated_at": "",
        "refined": None,
        "refinement_log": [],
    }
    rec["updated_at"] = rec["created_at"]
    store.ensure_initialized(SKILL)
    store.append_record(SKILL, rec)
    print(store.to_jsonl_line(rec))


def main() -> None:
    p = store.AhaArgParser(prog="dao")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="capture a dao record")
    a.add_argument("raw")
    a.add_argument("--tag", action="append", default=[])
    a.set_defaults(fn=cmd_add)

    args = p.parse_args()
    try:
        args.fn(args)
    except store.IdNotFound as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except store.CorruptRecord as e:
        print(f"Data error: {e}", file=sys.stderr); sys.exit(2)
    except (OSError, RuntimeError) as e:
        print(f"System error: {e}", file=sys.stderr); sys.exit(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/dao/tests/test_dao.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/dao
git commit -m "feat(dao): skeleton + add verb"
```

### Task 3.2: dao list

**Files:**
- Modify: `skills/dao/scripts/dao.py`
- Modify: `skills/dao/tests/test_dao.py`

- [ ] **Step 1: Write failing tests**

Append to `test_dao.py`:
```python
def test_list_jsonl(run):
    run("add", "one")
    run("add", "two")
    proc = run("list")
    lines = proc.stdout.strip().splitlines()
    assert len(lines) == 2
    for l in lines: json.loads(l)


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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/dao/tests/test_dao.py -v -k list`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `dao.py`:
```python
def cmd_list(args) -> None:
    records = store.filter_records(
        store.read_all(SKILL),
        since=args.since,
        until=args.until,
        tags=args.tag or None,
        limit=args.limit,
    )
    if args.tsv:
        print("\t".join(TSV_COLS))
        for r in records:
            print(store.to_tsv_row(r, TSV_COLS))
    else:
        for r in records:
            print(store.to_jsonl_line(r))
```

Register in `main()` (before `args = p.parse_args()`):
```python
    l = sub.add_parser("list", help="list dao records")
    l.add_argument("--tag", action="append", default=[])
    l.add_argument("--since", default=None)
    l.add_argument("--until", default=None)
    l.add_argument("--limit", type=int, default=None)
    l.add_argument("--tsv", action="store_true")
    l.set_defaults(fn=cmd_list)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/dao/tests/test_dao.py -v -k list`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/dao
git commit -m "feat(dao): list verb"
```

### Task 3.3: dao refine

**Files:**
- Modify: `skills/dao/scripts/dao.py`
- Modify: `skills/dao/tests/test_dao.py`

- [ ] **Step 1: Write failing tests**

Append to `test_dao.py`:
```python
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/dao/tests/test_dao.py -v -k refine`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `dao.py`:
```python
def cmd_refine(args) -> None:
    out = store.refine_record(SKILL, args.id, args.refined)
    print(store.to_jsonl_line(out))
```

Register in `main()`:
```python
    r = sub.add_parser("refine", help="set or update refined wording")
    r.add_argument("id")
    r.add_argument("refined")
    r.set_defaults(fn=cmd_refine)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/dao/tests/ -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add skills/dao
git commit -m "feat(dao): refine verb"
```

---

## Phase 4: tip CLI

### Task 4.1: tip skeleton + add

**Files:**
- Create: `skills/tip/__init__.py`, `skills/tip/scripts/__init__.py`, `skills/tip/tests/__init__.py`
- Create: `skills/tip/scripts/tip.py`
- Create: `skills/tip/tests/conftest.py`
- Create: `skills/tip/tests/test_tip.py`

- [ ] **Step 1: Write failing test**

Create `skills/tip/tests/conftest.py`:
```python
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tip.py"


@pytest.fixture
def aha_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AHA_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def run(aha_home):
    def _run(*args, expect_code: int = 0):
        env = {**os.environ, "AHA_HOME": str(aha_home)}
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == expect_code, (
            f"exit={proc.returncode}\n{proc.stdout}\n{proc.stderr}"
        )
        return proc
    return _run
```

Create `skills/tip/tests/test_tip.py`:
```python
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
```

Create empty `__init__.py` files.

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/tip/tests/test_tip.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

Create `skills/tip/scripts/tip.py`:
```python
#!/usr/bin/env python3
"""tip CLI."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
import store  # noqa: E402

SKILL = "tip"
TSV_COLS = ["id", "raw", "tags", "created_at"]


def cmd_add(args) -> None:
    rec = {
        "id": store.new_id(),
        "raw": args.raw,
        "tags": args.tag or [],
        "created_at": store.now_iso(),
        "updated_at": "",
    }
    rec["updated_at"] = rec["created_at"]
    store.ensure_initialized(SKILL)
    store.append_record(SKILL, rec)
    print(store.to_jsonl_line(rec))


def main() -> None:
    p = store.AhaArgParser(prog="tip")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="capture a tip")
    a.add_argument("raw")
    a.add_argument("--tag", action="append", default=[])
    a.set_defaults(fn=cmd_add)

    args = p.parse_args()
    try:
        args.fn(args)
    except store.IdNotFound as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except store.CorruptRecord as e:
        print(f"Data error: {e}", file=sys.stderr); sys.exit(2)
    except (OSError, RuntimeError) as e:
        print(f"System error: {e}", file=sys.stderr); sys.exit(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/tip/tests/test_tip.py -v -k add`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/tip
git commit -m "feat(tip): skeleton + add verb"
```

### Task 4.2: tip list

**Files:**
- Modify: `skills/tip/scripts/tip.py`
- Modify: `skills/tip/tests/test_tip.py`

- [ ] **Step 1: Write failing tests**

Append to `test_tip.py`:
```python
def test_list_jsonl(run):
    run("add", "one"); run("add", "two")
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/tip/tests/test_tip.py -v -k list`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `tip.py`:
```python
def cmd_list(args) -> None:
    records = store.filter_records(
        store.read_all(SKILL),
        since=args.since, until=args.until,
        tags=args.tag or None, limit=args.limit,
    )
    if args.tsv:
        print("\t".join(TSV_COLS))
        for r in records:
            print(store.to_tsv_row(r, TSV_COLS))
    else:
        for r in records:
            print(store.to_jsonl_line(r))
```

Register in `main()`:
```python
    l = sub.add_parser("list", help="list tips")
    l.add_argument("--tag", action="append", default=[])
    l.add_argument("--since", default=None)
    l.add_argument("--until", default=None)
    l.add_argument("--limit", type=int, default=None)
    l.add_argument("--tsv", action="store_true")
    l.set_defaults(fn=cmd_list)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/tip/tests/test_tip.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add skills/tip
git commit -m "feat(tip): list verb"
```

---

## Phase 5: task CLI

### Task 5.1: task skeleton + add

**Files:**
- Create: `skills/task/__init__.py`, `skills/task/scripts/__init__.py`, `skills/task/tests/__init__.py`
- Create: `skills/task/scripts/task.py`
- Create: `skills/task/tests/conftest.py`
- Create: `skills/task/tests/test_task.py`

- [ ] **Step 1: Write failing tests**

Create `skills/task/tests/conftest.py`:
```python
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "task.py"


@pytest.fixture
def aha_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AHA_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def run(aha_home):
    def _run(*args, expect_code: int = 0):
        env = {**os.environ, "AHA_HOME": str(aha_home)}
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == expect_code, (
            f"exit={proc.returncode}\n{proc.stdout}\n{proc.stderr}"
        )
        return proc
    return _run
```

Create `skills/task/tests/test_task.py`:
```python
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
```

Create empty `__init__.py` files.

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/task/tests/test_task.py -v -k add`
Expected: FAIL.

- [ ] **Step 3: Implement**

Create `skills/task/scripts/task.py`:
```python
#!/usr/bin/env python3
"""task CLI."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
import store  # noqa: E402

SKILL = "task"
STATUSES = ("open", "done", "dropped")
TSV_COLS = ["id", "raw", "status", "due", "tags", "created_at"]


def _iso_date(s: str) -> str:
    date.fromisoformat(s)
    return s


def cmd_add(args) -> None:
    rec = {
        "id": store.new_id(),
        "raw": args.raw,
        "tags": args.tag or [],
        "created_at": store.now_iso(),
        "updated_at": "",
        "due": args.due,
        "status": "open",
        "done_at": None,
        "log": [],
        "reflection": None,
    }
    rec["updated_at"] = rec["created_at"]
    store.ensure_initialized(SKILL)
    store.append_record(SKILL, rec)
    print(store.to_jsonl_line(rec))


def main() -> None:
    p = store.AhaArgParser(prog="task")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="capture a task")
    a.add_argument("raw")
    a.add_argument("--due", type=_iso_date, default=None)
    a.add_argument("--tag", action="append", default=[])
    a.set_defaults(fn=cmd_add)

    args = p.parse_args()
    try:
        args.fn(args)
    except store.IdNotFound as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except store.CorruptRecord as e:
        print(f"Data error: {e}", file=sys.stderr); sys.exit(2)
    except (OSError, RuntimeError) as e:
        print(f"System error: {e}", file=sys.stderr); sys.exit(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/task/tests/test_task.py -v -k add`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/task
git commit -m "feat(task): skeleton + add verb with --due validation"
```

### Task 5.2: task list

**Files:**
- Modify: `skills/task/scripts/task.py`
- Modify: `skills/task/tests/test_task.py`

- [ ] **Step 1: Write failing tests**

Append to `test_task.py`:
```python
def test_list_jsonl(run):
    run("add", "one"); run("add", "two")
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/task/tests/test_task.py -v -k list`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `task.py`:
```python
def cmd_list(args) -> None:
    records = store.filter_records(
        store.read_all(SKILL),
        since=args.since,
        until=args.until,
        tags=args.tag or None,
        status=args.status,
        due_before=args.due_before,
        limit=args.limit,
    )
    if args.tsv:
        print("\t".join(TSV_COLS))
        for r in records:
            print(store.to_tsv_row(r, TSV_COLS))
    else:
        for r in records:
            print(store.to_jsonl_line(r))
```

Register in `main()`:
```python
    l = sub.add_parser("list", help="list tasks")
    l.add_argument("--status", choices=STATUSES, default=None)
    l.add_argument("--tag", action="append", default=[])
    l.add_argument("--since", default=None)
    l.add_argument("--until", default=None)
    l.add_argument("--due-before", dest="due_before",
                   type=_iso_date, default=None)
    l.add_argument("--limit", type=int, default=None)
    l.add_argument("--tsv", action="store_true")
    l.set_defaults(fn=cmd_list)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/task/tests/test_task.py -v -k list`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/task
git commit -m "feat(task): list with --status/--due-before filters"
```

### Task 5.3: task log

**Files:**
- Modify: `skills/task/scripts/task.py`
- Modify: `skills/task/tests/test_task.py`

- [ ] **Step 1: Write failing tests**

Append to `test_task.py`:
```python
def test_log_appends(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("log", rid, "first note")
    rec = json.loads(proc.stdout.strip())
    assert rec["log"][-1]["note"] == "first note"


def test_log_unknown_id(run):
    run("log", "missing", "n", expect_code=1)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/task/tests/test_task.py -v -k test_log`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `task.py`:
```python
def cmd_log(args) -> None:
    out = store.append_log(SKILL, args.id, args.note)
    print(store.to_jsonl_line(out))
```

Register:
```python
    g = sub.add_parser("log", help="append a progress note")
    g.add_argument("id")
    g.add_argument("note")
    g.set_defaults(fn=cmd_log)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/task/tests/test_task.py -v -k test_log`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/task
git commit -m "feat(task): log verb"
```

### Task 5.4: task done

**Files:**
- Modify: `skills/task/scripts/task.py`
- Modify: `skills/task/tests/test_task.py`

- [ ] **Step 1: Write failing tests**

Append to `test_task.py`:
```python
def test_done_sets_status_and_done_at(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("done", rid)
    rec = json.loads(proc.stdout.strip())
    assert rec["status"] == "done"
    assert rec["done_at"]
    assert rec["reflection"] is None


def test_done_with_reflection(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("done", rid, "--reflection", "smooth")
    rec = json.loads(proc.stdout.strip())
    assert rec["reflection"] == "smooth"


def test_done_unknown_id(run):
    run("done", "missing", expect_code=1)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/task/tests/test_task.py -v -k test_done`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `task.py`:
```python
def cmd_done(args) -> None:
    out = store.mark_done(SKILL, args.id, args.reflection)
    print(store.to_jsonl_line(out))
```

Register:
```python
    d = sub.add_parser("done", help="mark task done")
    d.add_argument("id")
    d.add_argument("--reflection", default=None)
    d.set_defaults(fn=cmd_done)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/task/tests/test_task.py -v -k test_done`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/task
git commit -m "feat(task): done verb"
```

### Task 5.5: task drop

**Files:**
- Modify: `skills/task/scripts/task.py`
- Modify: `skills/task/tests/test_task.py`

- [ ] **Step 1: Write failing tests**

Append to `test_task.py`:
```python
def test_drop_sets_status_dropped(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("drop", rid)
    rec = json.loads(proc.stdout.strip())
    assert rec["status"] == "dropped"
    assert rec["done_at"]


def test_drop_with_reflection(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("drop", rid, "--reflection", "no longer needed")
    rec = json.loads(proc.stdout.strip())
    assert rec["reflection"] == "no longer needed"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/task/tests/test_task.py -v -k test_drop`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `task.py`:
```python
def cmd_drop(args) -> None:
    out = store.mark_dropped(SKILL, args.id, args.reflection)
    print(store.to_jsonl_line(out))
```

Register:
```python
    dr = sub.add_parser("drop", help="mark task dropped")
    dr.add_argument("id")
    dr.add_argument("--reflection", default=None)
    dr.set_defaults(fn=cmd_drop)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/task/tests/test_task.py -v -k test_drop`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/task
git commit -m "feat(task): drop verb"
```

### Task 5.6: task set-due

**Files:**
- Modify: `skills/task/scripts/task.py`
- Modify: `skills/task/tests/test_task.py`

- [ ] **Step 1: Write failing tests**

Append to `test_task.py`:
```python
def test_set_due_updates_field(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("set-due", rid, "2026-07-15")
    rec = json.loads(proc.stdout.strip())
    assert rec["due"] == "2026-07-15"


def test_set_due_invalid_date(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    run("set-due", rid, "not-a-date", expect_code=1)


def test_set_due_unknown_id(run):
    run("set-due", "missing", "2026-07-15", expect_code=1)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest skills/task/tests/test_task.py -v -k set_due`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `task.py`:
```python
def cmd_set_due(args) -> None:
    out = store.update_record(SKILL, args.id, lambda r: {**r, "due": args.due})
    print(store.to_jsonl_line(out))
```

Register:
```python
    sd = sub.add_parser("set-due", help="update due date")
    sd.add_argument("id")
    sd.add_argument("due", type=_iso_date)
    sd.set_defaults(fn=cmd_set_due)
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest skills/task/tests/ -v`
Expected: all task tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/task
git commit -m "feat(task): set-due verb"
```

---

## Phase 6: SKILL.md files

### Task 6.1: idea SKILL.md

**Files:**
- Create: `skills/idea/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `skills/idea/SKILL.md`:
```markdown
---
name: idea
description: Capture a fleeting outward-facing creative impulse — anything from a half-formed product idea to a future side project. Triggers on Chinese 想法/灵感/点子/创意/idea/我有个想法 and English I have an idea / brainstorm / what if we / project idea / explore. Use when the user wants to record something they could later act on, distinct from internal insight (dao), tactical shortcuts (tip), or to-dos (task).
version: 0.1.0
---

# idea

`idea` captures outward-facing impulses — sparks of "we could build X" or "what if we tried Y." It is the entry point for the lifecycle: capture → refine → decide. The agent records, suggests refinements, and surfaces related ideas; it never decides for the user, never auto-promotes to task, never overwrites raw.

## Triggers

- 我有个想法 / 想到一个点子 / 这个 idea 不错
- I have an idea / what if we / project idea / brainstorm this
- Slash: /idea

## Storage

Records live at `$HOME/aha/idea.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/idea/scripts/idea.py <verb> ...`.

- `add <raw> [--tag T...] [--status S]` — capture a new idea. Outputs the full record as one JSON line.
- `list [--tag T...] [--status S] [--since DATE] [--until DATE] [--limit N] [--tsv]` — browse. Default JSONL (one record per line). `--tsv` prints columns `id, raw, refined, status, tags, created_at` with truncated cells.
- `refine <id> <new_refined>` — set or update the refined wording. The previous `refined`, if non-null, is archived into `refinement_log[]` with timestamp. `raw` never changes.
- `set-status <id> <status>` — free-form status string (e.g. `incubating`, `decided`, `parked`).

## Constraints

- `raw` is immutable after first write. Refinement goes in `refined`; old `refined` versions are archived in `refinement_log` automatically.
- Status is free-form and advisory. Do not invent a state machine or auto-advance status.
- Cross-skill links use tags only. Do not mint links/parent fields.
- Suggest refinements; do not silently overwrite.

## Examples

```bash
python skills/idea/scripts/idea.py add "用 JSONL 替代 markdown 做事实源" --tag aha-skills --status incubating
python skills/idea/scripts/idea.py list --tag aha-skills --tsv
python skills/idea/scripts/idea.py refine 2026-05-19-a3f7 "数据是核心,工具附着"
python skills/idea/scripts/idea.py set-status 2026-05-19-a3f7 decided
```
```

- [ ] **Step 2: Verify**

Run: `head -5 skills/idea/SKILL.md`
Expected: shows `---\nname: idea\n...`.

- [ ] **Step 3: Commit**

```bash
git add skills/idea/SKILL.md
git commit -m "docs(idea): SKILL.md"
```

### Task 6.2: dao SKILL.md

**Files:**
- Create: `skills/dao/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `skills/dao/SKILL.md`:
```markdown
---
name: dao
description: Capture an inward-facing realization, principle, or methodology — the "道" or aha moment that names how things work. Triggers on Chinese 感悟/领悟/方法论/道/原则/aha/想明白了 and English insight / realization / principle / methodology / lesson learned. Use when the user is naming a pattern they noticed (internal), distinct from outward ideas (idea), tactical tips (tip), or work to do (task).
version: 0.1.0
---

# dao

`dao` records the moment a pattern crystallizes. It preserves the user's exact words (`raw`), then optionally distills them (`refined`) without ever erasing the original. The agent may suggest a tighter phrasing, surface related dao through tags, or invite a deeper conversation — but the wording belongs to the user.

## Triggers

- 我突然意识到 / 这个其实就是 / 想明白了 / 这是一种 ...
- insight / realization / lesson learned / I just realized
- Slash: /dao

## Storage

Records live at `$HOME/aha/dao.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/dao/scripts/dao.py <verb> ...`.

- `add <raw> [--tag T...]` — capture a dao. Outputs the full record as one JSON line.
- `list [--tag T...] [--since DATE] [--until DATE] [--limit N] [--tsv]` — browse. Default JSONL. `--tsv` prints columns `id, raw, refined, tags, created_at`.
- `refine <id> <new_refined>` — set or update refined wording. Previous `refined`, if any, is archived to `refinement_log[]`. `raw` never changes.

## Constraints

- `raw` is immutable. Never edit a user's exact phrasing — refine into `refined` instead.
- A "deep talk" or follow-up conversation does not need its own verb; the outcome is one more refinement.
- No status — dao does not have stages.
- Cross-skill links via tags only.

## Examples

```bash
python skills/dao/scripts/dao.py add "好脚手架是替你说不的人,不是替你说是的人"
python skills/dao/scripts/dao.py list --tag 系统设计 --tsv
python skills/dao/scripts/dao.py refine 2026-05-19-1c2f "好的脚手架替你说不"
```
```

- [ ] **Step 2: Commit**

```bash
git add skills/dao/SKILL.md
git commit -m "docs(dao): SKILL.md"
```

### Task 6.3: tip SKILL.md

**Files:**
- Create: `skills/tip/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `skills/tip/SKILL.md`:
```markdown
---
name: tip
description: Record a small actionable shortcut — a CLI flag, keystroke, workaround, or "did you know" trick. Triggers on Chinese 小技巧/小妙招/有个捷径/小贴士/快捷方式 and English shortcut / trick / pro tip / hack / lifehack. Use for tactical, repeatable techniques. Distinct from outward ideas (idea), inward insights (dao), and to-dos (task).
version: 0.1.0
---

# tip

`tip` is the lightweight bucket for "tiny things that save time." No status, no refinement — just record the trick with tags so future you (or `reflect`) can find it again. If a tip generalizes into a principle, write a new `dao`; the tip stays as the original observation.

## Triggers

- 教你一招 / 小妙招 / 我有个捷径 / 这个快捷方式
- pro tip / shortcut / trick / lifehack
- Slash: /tip

## Storage

Records live at `$HOME/aha/tip.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/tip/scripts/tip.py <verb> ...`.

- `add <raw> [--tag T...]` — capture a tip.
- `list [--tag T...] [--since DATE] [--until DATE] [--limit N] [--tsv]` — browse. Default JSONL. `--tsv` prints columns `id, raw, tags, created_at`.

## Constraints

- `raw` is immutable.
- No `refined`, no `status` — keep tip lean.
- Generalization = new `dao`, not a tip rewrite.
- Cross-skill links via tags only.

## Examples

```bash
python skills/tip/scripts/tip.py add "git commit --fixup <sha> 配合 rebase --autosquash" --tag git
python skills/tip/scripts/tip.py list --tag vim --tsv
```
```

- [ ] **Step 2: Commit**

```bash
git add skills/tip/SKILL.md
git commit -m "docs(tip): SKILL.md"
```

### Task 6.4: task SKILL.md

**Files:**
- Create: `skills/task/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `skills/task/SKILL.md`:
```markdown
---
name: task
description: Track a concrete to-do item along with its log of progress notes and a post-hoc reflection. Triggers on Chinese 待办/任务/todo/记一下日志/check-in/复盘 and English task / todo / log this / check in / retro this. Use when the user wants something they will later finish or drop, distinct from open-ended ideas (idea), insights (dao), or shortcuts (tip).
version: 0.1.0
---

# task

`task` couples capture with rhythm. It holds: `raw` (what to do), `due` (optional date), `status` ∈ {open, done, dropped}, `log[]` (append-only progress notes), and `reflection` (post-hoc summary set when done or dropped). Status is the only enum in the system; everything else stays free-form. The agent suggests next steps and surfaces stale tasks but never auto-completes, auto-extends due dates, or deletes records.

## Triggers

- 待办 / 加一个 task / todo / 记一下今天搞了什么 / 复盘一下
- task / todo / log this / check in / retro this
- Slash: /task

## Storage

Records live at `$HOME/aha/task.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/task/scripts/task.py <verb> ...`.

- `add <raw> [--due YYYY-MM-DD] [--tag T...]` — capture a task; status starts `open`.
- `list [--status S] [--tag T...] [--since DATE] [--until DATE] [--due-before DATE] [--limit N] [--tsv]` — browse. Default JSONL. `--tsv` prints columns `id, raw, status, due, tags, created_at`.
- `log <id> <note>` — append a progress note (timestamped, append-only).
- `done <id> [--reflection R]` — mark `done`; sets `done_at`; optional reflection.
- `drop <id> [--reflection R]` — mark `dropped`; sets `done_at`; optional reflection.
- `set-due <id> <YYYY-MM-DD>` — update due date.

## Constraints

- `raw` is immutable.
- `status` is the only enum: `open | done | dropped`. Do not invent intermediate states like `paused` or `blocked` — capture nuance in a `log` note instead.
- `log` is append-only. Never rewrite or remove entries.
- Past-due tasks do not auto-extend. The agent may suggest a new due date; only the user accepts.
- Cross-skill links via tags only.

## Examples

```bash
python skills/task/scripts/task.py add "写 aha-skills 验收 doc" --due 2026-05-30 --tag aha-skills
python skills/task/scripts/task.py log 2026-05-19-2b8e "今天走查了 store.py"
python skills/task/scripts/task.py list --status open --due-before 2026-06-01 --tsv
python skills/task/scripts/task.py done 2026-05-19-2b8e --reflection "切片切对了,锁工作"
```
```

- [ ] **Step 2: Commit**

```bash
git add skills/task/SKILL.md
git commit -m "docs(task): SKILL.md"
```

### Task 6.5: reflect SKILL.md

**Files:**
- Create: `skills/reflect/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `skills/reflect/SKILL.md`:
```markdown
---
name: reflect
description: Cross-skill pattern surfacing across idea/dao/tip/task within a time window. Triggers on Chinese 复盘/回顾/最近一段/这段时间/抽个空看看/总结 and English reflect / retro / what happened / weekly review / surface patterns. Use when the user wants the agent to read across all four record-producing skills (idea, dao, tip, task) and synthesize themes — not to add anything new.
version: 0.1.0
---

# reflect

`reflect` is the only read-only skill. It has no Python script. The agent itself is the reflection engine: it reads the four `.jsonl` files via the existing `list` verbs, groups by tag/time/status, and proposes themes back to the user as suggestions. Suggestions never become actions without the user's go-ahead.

## Triggers

- 复盘最近 / 这周回顾 / 这段时间我都干了啥 / 帮我看看模式
- reflect / retro / what have I been doing / weekly review / surface patterns
- Slash: /reflect

## Approach

When invoked:

1. Pick the time window. Default: last 14 days. Honor an explicit user-given window.
2. Pull data in parallel:
   ```
   python skills/idea/scripts/idea.py list --since YYYY-MM-DD
   python skills/dao/scripts/dao.py  list --since YYYY-MM-DD
   python skills/tip/scripts/tip.py  list --since YYYY-MM-DD
   python skills/task/scripts/task.py list --since YYYY-MM-DD
   ```
3. Aggregate in context:
   - tag frequency per skill and across skills
   - cross-source tag co-occurrences
   - task status distribution (open/done/dropped/overdue)
   - notable refinements (idea/dao records with non-empty `refinement_log`)
4. Surface 3-5 themes. Each theme cites at least one source `id` from the underlying records.
5. Offer suggestions ("would you like to ..."): triage suggestions for stale tasks, generalization candidates from repeated tips, candidate links between idea/dao that share tags. **Do not execute** the suggestions.

## Constraints

- **Read-only**: never call `add`, `refine`, `set-status`, `log`, `done`, `drop`, or `set-due`.
- **No fabrication**: every theme must trace to ≥1 record id present in the data pulled.
- **No auto-linking**: do not invent shared tags, parent fields, or bidirectional relationships in the data — surfacing is in the conversation, not in the JSONL.
- **Suggestions only**: questions remain open until the user replies; then route the response to the appropriate skill.

## Why no script

The actual work — reading, aggregating, synthesizing — is what the agent already does well. A script would freeze a particular synthesis shape into code; reflection's value is precisely that each pass can pick a different lens. Keep it as a prompt, not a pipeline.

## Examples

User: "帮我复盘最近两周的 aha-skills 工作"
Agent: pulls `--since 2026-05-05` from all four skills, finds tag `aha-skills` co-occurring across 1 idea, 3 dao, 5 task entries, surfaces themes (e.g. "两次 dao 都在讨论 schema 简化"), suggests "要不要把这两个 dao refine 成一条原则?" — and waits for confirmation before invoking `dao refine`.
```

- [ ] **Step 2: Commit**

```bash
git add skills/reflect/SKILL.md
git commit -m "docs(reflect): SKILL.md (script-less, agent-driven)"
```

---

## Phase 7: Project files

### Task 7.1: run_tests.py

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/run_tests.py`

- [ ] **Step 1: Implement**

Create `scripts/__init__.py` (empty).

Create `scripts/run_tests.py`:
```python
#!/usr/bin/env python3
"""Run the full pytest suite for skills/."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    return subprocess.call(
        [sys.executable, "-m", "pytest", "skills", "-v", *sys.argv[1:]],
        cwd=ROOT,
    )


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run full suite via runner**

Run: `python scripts/run_tests.py`
Expected: all tests pass (≥40 store + ≥6 idea + ≥4 dao + ≥4 tip + ≥10 task).

- [ ] **Step 3: Commit**

```bash
git add scripts
git commit -m "chore: scripts/run_tests.py wraps pytest skills/"
```

### Task 7.2: Makefile

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Implement**

Create `Makefile`:
```makefile
PYTHON ?= python3

.PHONY: test idea dao tip task help

help:
	@echo "make test   - run full pytest suite"
	@echo "make idea   - run idea CLI (pass args via ARGS=...)"
	@echo "make dao    - run dao CLI"
	@echo "make tip    - run tip CLI"
	@echo "make task   - run task CLI"

test:
	$(PYTHON) scripts/run_tests.py

idea:
	$(PYTHON) skills/idea/scripts/idea.py $(ARGS)

dao:
	$(PYTHON) skills/dao/scripts/dao.py $(ARGS)

tip:
	$(PYTHON) skills/tip/scripts/tip.py $(ARGS)

task:
	$(PYTHON) skills/task/scripts/task.py $(ARGS)
```

- [ ] **Step 2: Verify**

Run: `make test`
Expected: full suite passes.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: Makefile (test + per-skill runners)"
```

### Task 7.3: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Implement**

Create `README.md`:
```markdown
# aha-skills

Low-friction capture of fleeting cognition — so it can be retrieved, refined, reviewed, and grown.

Five skills:

- **idea** — outward sparks: capture → incubate → decide.
- **dao** — inward realizations: original phrasing preserved, distillation layered on top.
- **tip** — small tactical shortcuts.
- **task** — to-dos with progress log and post-hoc reflection.
- **reflect** — agent-driven cross-skill pattern surfacing (read-only).

## Design tenets

1. JSONL is the only source of truth. One file per skill at `~/aha/<skill>.jsonl`, one JSON record per line.
2. The user's `raw` input is immutable. Refinement goes into `refined`; older versions are archived in `refinement_log`.
3. The agent edits JSONL **only** through Python scripts — no free-form file edits.
4. No forced workflows. The agent suggests; the user decides.

See `docs/superpowers/specs/2026-05-19-aha-skills-redesign-design.md` for full design and rationale.

## Layout

```
skills/
  _lib/store.py         shared lib (paths, ids, locking, JSONL CRUD)
  idea/SKILL.md + scripts/idea.py
  dao/SKILL.md  + scripts/dao.py
  tip/SKILL.md  + scripts/tip.py
  task/SKILL.md + scripts/task.py
  reflect/SKILL.md      (no script — agent-driven)
scripts/run_tests.py
Makefile
```

## Quickstart

```bash
make test                                                    # run the suite
make idea ARGS="add '用 JSONL 替代 Markdown' --tag aha-skills"
make task ARGS="add 'ship redesign' --due 2026-05-30"
make task ARGS="list --status open --tsv"
```

Data location: `$HOME/aha/<skill>.jsonl`. Override with `AHA_HOME=/path/to/dir`.

## Requirements

- Python 3.11+
- macOS or Linux (uses `fcntl.flock`)
- pytest (dev only)

## Conventions

- `id`: `YYYY-MM-DD-xxxx` (4 hex chars)
- `created_at`/`updated_at`: ISO 8601 with local UTC offset
- Cross-skill linkage: tags only, shared namespace
- Errors: exit 0 success, exit 1 user error, exit 2 data/system error
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README"
```

### Task 7.4: Refresh .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Edit**

Remove the `aha-workspace/` line from `.gitignore` (the directory has been deleted; data now lives in `$HOME/aha/`, outside the repo). Replace the section labeled `# Runtime workspace produced by skills (idea inbox, etc.)` and the line `aha-workspace/` with:

```
# Local data lives outside the repo at $HOME/aha/ (or $AHA_HOME); nothing to ignore here.
```

- [ ] **Step 2: Verify**

Run: `git diff .gitignore`
Expected: only the runtime-workspace block changes.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore(gitignore): drop aha-workspace ignore (data now at \$HOME/aha)"
```

### Task 7.5: Final verification + LOC budget check

**Files:** none

- [ ] **Step 1: Run full test suite**

Run: `make test`
Expected: 0 failures across all skills (~60+ tests).

- [ ] **Step 2: Verify production LOC budget**

Run:
```bash
find skills -name '*.py' -not -path '*/tests/*' -not -name 'conftest.py' \
  -not -name '__init__.py' | xargs wc -l | tail -1
```
Expected: total ≤ 1050 lines (spec §16 verification #5).

- [ ] **Step 3: Verify no test files contain placeholders**

Run:
```bash
grep -rn 'TBD\|TODO\|FIXME\|XXX\|placeholder' skills/ scripts/ Makefile README.md docs/ || echo "clean"
```
Expected: `clean`.

- [ ] **Step 4: Smoke test the round trip with real Chinese**

Run:
```bash
TMPHOME=$(mktemp -d); export AHA_HOME="$TMPHOME"
python skills/idea/scripts/idea.py add "用 JSONL 替代 Markdown" --tag 测试 --status incubating
python skills/idea/scripts/idea.py list --tsv
grep -c '\\u' "$AHA_HOME/idea.jsonl"
unset AHA_HOME; rm -rf "$TMPHOME"
```
Expected: list shows the Chinese raw; `grep -c '\u'` prints `0` (no escaped Unicode).

- [ ] **Step 5: Commit nothing — verification only.**

If anything failed, fix the offending task and re-run before signing off.

---

## Self-Review

Before handoff, run through these checks (the writer's responsibility, not the executor's):

**1. Spec coverage:**
- Phase 1 implements every API in spec §7.3 (paths, ids, ts, exceptions, ensure_initialized, read_all, find_by_id, filter_records, append_record, update_record, refine_record, append_log, mark_done, mark_dropped, to_jsonl_line, to_tsv_row, AhaArgParser, locked, _atomic_write_lines).
- Phases 2–5 implement all 15 verbs from spec §8.2 (idea: add/list/refine/set-status; dao: add/list/refine; tip: add/list; task: add/list/log/done/drop/set-due).
- Phase 6 produces 5 SKILL.md files (idea/dao/tip/task/reflect) per spec §13.
- Phase 7 produces run_tests.py (§7.1), Makefile (§16 #12), README, and gitignore cleanup (§14).
- Concurrency tests (§16 #8) live in Task 1.16. Five immutability tests (§6.5) live in Tasks 1.10–1.14.
- Verification criteria from spec §16 are exercised by Task 7.5.

**2. Placeholder scan:** No `TBD`, `TODO`, "implement later", "similar to Task N", or "add appropriate error handling" anywhere. Each step has actual code or actual commands.

**3. Type/name consistency:**
- `Skill = Literal["idea", "dao", "tip", "task"]` defined in Task 1.1 and used as `skill: str` in subsequent tasks (consistent — all functions accept `str`, the Literal is a doc hint).
- `AhaError`/`IdNotFound`/`CorruptRecord` defined in Task 1.3, caught in CLI mains in Tasks 2.1, 3.1, 4.1, 5.1 (consistent).
- `STATUSES = ("open", "done", "dropped")` defined in Task 5.1, referenced in Task 5.2 list filter (consistent).
- `TSV_COLS` differs per skill (idea: 6 cols incl. status/refined; dao: 5 cols incl. refined; tip: 4 cols; task: 6 cols incl. status/due) — matches spec §8.3 and the per-skill schema in §6.3.
- `_iso_date` helper in Task 5.1 reused in 5.2 and 5.6 (consistent).
- `refine_record` (Task 1.12), `append_log` (1.13), `mark_done`/`mark_dropped` (1.14) — all delegate to `update_record` (1.11), so behavior under flock + updated_at bump is uniform.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-19-aha-skills-redesign.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
