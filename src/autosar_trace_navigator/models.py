"""Immutable syntax results; RTE data dependencies belong to a later resolver."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class SourceRange:
    """One-based lines/byte columns; end position and byte offset are exclusive."""

    path: Path
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_byte: int
    end_byte: int


@dataclass(frozen=True)
class FunctionDefinition:
    id: str
    name: str
    location: SourceRange
    body_location: SourceRange
    uncertainty: tuple[str, ...]


@dataclass(frozen=True)
class FunctionCall:
    caller_id: str | None
    branch_id: str | None
    expression: str
    callee_expression: str
    callee_name: str | None
    kind: Literal["direct_candidate", "macro", "indirect"]
    location: SourceRange
    uncertainty: tuple[str, ...]


@dataclass(frozen=True)
class Branch:
    id: str
    function_id: str | None
    kind: Literal["if", "else_if", "else"]
    condition: str | None
    location: SourceRange
    body_location: SourceRange
    parent_id: str | None
    chain_id: str
    uncertainty: tuple[str, ...]


@dataclass(frozen=True)
class ParseDiagnostic:
    code: str
    message: str
    location: SourceRange


@dataclass(frozen=True)
class ParseResult:
    path: Path
    functions: tuple[FunctionDefinition, ...]
    calls: tuple[FunctionCall, ...]
    branches: tuple[Branch, ...]
    diagnostics: tuple[ParseDiagnostic, ...]


@dataclass(frozen=True)
class ValueProbe:
    """A value to investigate at a source use site, not a solved constraint."""

    function_id: str
    expression: str
    location: SourceRange
    kind: Literal["variable", "return"] = "variable"
