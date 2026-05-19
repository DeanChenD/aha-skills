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
