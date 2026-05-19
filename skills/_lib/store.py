"""aha-skills shared store: JSONL CRUD, ids, timestamps, locking."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import secrets
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

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


def new_id() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{today}-{secrets.token_hex(2)}"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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


def ensure_initialized(skill: str) -> None:
    p = jsonl_path(skill)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.touch()


def read_all(skill: str) -> list[dict]:
    # Unlocked read: writers always go through _atomic_write_lines, whose
    # os.replace is atomic on POSIX, so a reader sees either the old file
    # or the new file in full — never a torn write. Spec §10.2.
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


def find_by_id(skill: str, id: str) -> dict | None:
    for rec in read_all(skill):
        if rec.get("id") == id:
            return rec
    return None


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


_thread_locks: dict[str, threading.Lock] = {}
_thread_locks_guard = threading.Lock()


def _thread_lock_for(path: Path) -> threading.Lock:
    key = str(path)
    with _thread_locks_guard:
        lock = _thread_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _thread_locks[key] = lock
        return lock


@contextmanager
def locked(path: Path):
    # Two-tier lock: thread-level Lock first (fcntl.flock is per-OFD on POSIX,
    # so two threads in the same process opening the file would each get an
    # independent flock), then fcntl for cross-process serialization.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    tlock = _thread_lock_for(path)
    with tlock:
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


def append_record(skill: str, record: dict) -> None:
    p = jsonl_path(skill)
    line = to_jsonl_line(record) + "\n"
    with locked(p) as f:
        f.seek(0, os.SEEK_END)
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


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


def append_log(skill: str, id: str, note: str) -> dict:
    def mutate(rec: dict) -> dict:
        out = dict(rec)
        log = list(out.get("log") or [])
        log.append({"at": now_iso(), "note": note})
        out["log"] = log
        return out

    return update_record(skill, id, mutate)


def mark_done(skill: str, id: str, reflection: str | None = None) -> dict:
    def mutate(rec: dict) -> dict:
        out = dict(rec)
        out["status"] = "done"
        out["done_at"] = now_iso()
        if reflection is not None:
            out["reflection"] = reflection
        return out

    return update_record(skill, id, mutate)


def mark_dropped(skill: str, id: str, reflection: str | None = None) -> dict:
    def mutate(rec: dict) -> dict:
        out = dict(rec)
        out["status"] = "dropped"
        if reflection is not None:
            out["reflection"] = reflection
        return out

    return update_record(skill, id, mutate)


class AhaArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        sys.stderr.write(f"Error: {message}\n")
        self.print_usage(sys.stderr)
        sys.exit(1)
