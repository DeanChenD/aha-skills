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


import secrets
from datetime import datetime


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
