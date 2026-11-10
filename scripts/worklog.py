"""Create portable task/session Markdown records using only the standard library."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
from string import Template
import subprocess
import uuid

TASK_ID = re.compile(r"[A-Z][A-Z0-9]{1,11}-[0-9]{3,6}\Z")
ACTOR = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,39}\Z")
TOOLS = ("codex", "claude", "human")


def validate_id(task_id: str) -> str:
    """Reject paths and require a stable identifier such as TASK-010."""
    if not TASK_ID.fullmatch(task_id):
        raise ValueError("작업 ID 형식: TASK-010 (영문 대문자 접두사-숫자 3~6자리)")
    return task_id


def git_value(root: Path, *args: str) -> str:
    """Read Git metadata without changing the index, branch, or remote."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "확인 불가"
    return result.stdout.strip() if result.returncode == 0 else "확인 불가"


def write_record(root: Path, kind: str, filename: str, values: dict[str, str]) -> Path:
    """Fill a repository template and exclusively create a UTF-8 Markdown file."""
    work = root / "docs/work"
    template_name = "task.md" if kind == "tasks" else "session.md"
    content = Template((work / "templates" / template_name).read_text(encoding="utf-8")).substitute(values)
    target = work / kind / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
    return target


def create_task(root: Path, task_id: str, title: str) -> Path:
    """Create a planned card; never replace an existing task or assign it."""
    validate_id(task_id)
    title = title.strip()
    if not title or any(ord(char) < 32 or ord(char) == 127 for char in title):
        raise ValueError("제목은 비어 있지 않은 한 줄이어야 합니다.")
    return write_record(root, "tasks", task_id + ".md", {
        "task_id": task_id, "title": title,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_commit": git_value(root, "rev-parse", "HEAD"),
    })


def create_session(root: Path, task_id: str, tool: str, actor: str) -> Path:
    """Create a unique session linked to an existing card, leaving the card intact."""
    validate_id(task_id)
    if tool not in TOOLS or not ACTOR.fullmatch(actor):
        raise ValueError("도구는 codex/claude/human, 담당은 영문·숫자·._- 별칭(1~40자)을 사용하세요.")
    if not (root / "docs/work/tasks" / (task_id + ".md")).is_file():
        raise ValueError(f"작업 카드가 없습니다: {task_id}")
    now = datetime.now(timezone.utc)
    filename = f"{now:%Y%m%dT%H%M%SZ}-{tool}-{uuid.uuid4().hex}.md"
    return write_record(root, "sessions", filename, {
        "task_id": task_id, "tool": tool, "actor": actor,
        "created_at": now.isoformat(timespec="seconds"),
        "branch": git_value(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "base_commit": git_value(root, "rev-parse", "HEAD"),
    })


def list_tasks(root: Path) -> list[Path]:
    """List canonical cards in stable order without performing any writes."""
    return sorted(path for path in (root / "docs/work/tasks").glob("*.md") if TASK_ID.fullmatch(path.stem))


def main(argv: list[str] | None = None) -> int:
    """Run the CLI from any working directory; paths are relative to this repository."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="작업 카드 경로 표시 (읽기 전용)")
    new = commands.add_parser("new", help="새 작업 카드 생성")
    new.add_argument("task_id")
    new.add_argument("--title", required=True)
    start = commands.add_parser("start", help="기존 작업의 새 세션 기록 생성")
    start.add_argument("task_id")
    start.add_argument("--tool", choices=TOOLS, required=True)
    start.add_argument("--actor", required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    try:
        if args.command == "list":
            for path in list_tasks(root):
                print(path.relative_to(root).as_posix())
        else:
            target = (create_task(root, args.task_id, args.title) if args.command == "new"
                      else create_session(root, args.task_id, args.tool, args.actor))
            print(target.relative_to(root).as_posix())
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
