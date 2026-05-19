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
