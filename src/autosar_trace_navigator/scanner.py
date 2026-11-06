"""Read-only discovery of C sources and headers, independent of the parser."""

from collections.abc import Iterable
from dataclasses import dataclass
import os
from pathlib import Path
import stat


@dataclass(frozen=True)
class SourceFile:
    """A discovered file with absolute and scan-root-relative locations."""

    path: Path
    relative_path: Path

    @property
    def is_rte_header(self) -> bool:
        """Recognize Rte_*.h names; this does not prove generated provenance."""
        return self.path.suffix.lower() == ".h" and self.path.name.lower().startswith("rte_")


def _raise_walk_error(error: OSError) -> None:
    raise error


def _is_link(path: Path) -> bool:
    info = path.lstat()
    # Include Windows junctions/reparse points on Python 3.11 as well.
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def scan_sources(
    root: str | os.PathLike[str],
    *,
    exclude_paths: Iterable[str | os.PathLike[str]] = (),
    include_paths: Iterable[str | os.PathLike[str]] = (),
) -> tuple[SourceFile, ...]:
    """Find .c/.h files recursively without reading or changing their contents.

    Exclusions are literal files/directories, not globs. Relative exclusions are
    interpreted against root, and exclusions outside root are rejected. There
    are no implicit exclusions. Optional literal include paths restrict discovery;
    unselected directories are pruned before entering them. Empty includes mean
    the whole root for compatibility. Results have a stable relative POSIX-path order.
    Directory symlinks/junctions and file symlinks are skipped. An explicitly
    supplied root is resolved first. Filesystem errors propagate instead of
    returning a misleading partial result.
    """
    base = Path(root).resolve(strict=True)
    if not stat.S_ISDIR(base.stat().st_mode):
        raise NotADirectoryError(f"Scan root is not a directory: {base}")

    excluded = []
    for item in exclude_paths:
        candidate = Path(item)
        if not candidate.is_absolute():
            candidate = base / candidate
        candidate = candidate.resolve()
        if not candidate.is_relative_to(base):
            raise ValueError(f"Excluded path must be inside scan root: {candidate}")
        excluded.append(candidate)

    def is_excluded(path: Path) -> bool:
        return any(path.is_relative_to(item) for item in excluded)

    included = []
    for item in include_paths:
        candidate = Path(item)
        if not candidate.is_absolute():
            candidate = base / candidate
        candidate = candidate.resolve(strict=True)
        if not candidate.is_relative_to(base):
            raise ValueError(f"Included path must be inside scan root: {candidate}")
        included.append(candidate)

    def is_selected(path: Path, *, directory: bool = False) -> bool:
        return not included or any(path.is_relative_to(item) or
                                   (directory and item.is_relative_to(path)) for item in included)

    if is_excluded(base):
        return ()

    found = []
    for directory, directories, filenames in os.walk(
        base, topdown=True, onerror=_raise_walk_error, followlinks=False
    ):
        parent = Path(directory)
        directories[:] = sorted(
            name for name in directories
            if is_selected(parent / name, directory=True)
            and not is_excluded(parent / name) and not _is_link(parent / name)
        )
        for name in filenames:
            path = parent / name
            if path.suffix.lower() not in {".c", ".h"}:
                continue
            if not is_selected(path) or is_excluded(path) or _is_link(path):
                continue
            # stat errors (including files removed during discovery) propagate.
            if stat.S_ISREG(path.stat().st_mode):
                found.append(SourceFile(path=path, relative_path=path.relative_to(base)))

    return tuple(sorted(found, key=lambda source: source.relative_path.as_posix()))
