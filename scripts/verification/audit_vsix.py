"""Compare a checked-in VSIX to a compiled checkout without installing or opening any UI."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import zipfile


def audit(extension: Path) -> dict:
    """Read package contents only; never extract files or modify the checkout."""
    extension = extension.resolve()
    package = extension.parent.parent / "release/branch-investigation-0.1.0.vsix"
    compiled = extension / "dist/src"
    if not compiled.is_dir():
        raise ValueError("Run npm test or npm run compile in the extension first")
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("extension/package.json"))
        source_manifest = json.loads((extension / "package.json").read_text(encoding="utf-8"))
        expected = {"extension/dist/src/" + path.relative_to(compiled).as_posix(): path for path in compiled.rglob("*.js")}
        archived = {name for name in names if name.startswith("extension/dist/src/") and name.endswith(".js")}
        mismatches, line_endings_only = [], []
        for name, path in expected.items():
            actual = archive.read(name) if name in archived else None
            if actual != path.read_bytes():
                if actual is not None and actual.replace(b"\r\n", b"\n") == path.read_bytes().replace(b"\r\n", b"\n"):
                    line_endings_only.append(name)
                else:
                    mismatches.append(name)
        readme = next(name for name in names if name.lower() == "extension/readme.md")
        packaged_readme = archive.read(readme).decode("utf-8").replace("\r\n", "\n")
        source_readme = (extension / "README.md").read_text(encoding="utf-8")
        readme_matches = packaged_readme == source_readme
        # VSCE rewrites relative Markdown links. Distinguish this from stale/missing prose.
        link = re.compile(r"\]\(([^)]+)\)")
        readme_text_matches = link.sub("]()", packaged_readme) == link.sub("]()", source_readme)
        parent_links = [target for target in link.findall(packaged_readme)
                        if urlsplit(target).hostname == "github.com" and ".." in urlsplit(target).path.split("/")]
        dev_files = [name for name in names if "/node_modules/" in name or name.startswith("extension/test/")]
        result = {"sha256": hashlib.sha256(package.read_bytes()).hexdigest(), "bytes": package.stat().st_size,
                  "manifestMatches": manifest == source_manifest, "readmeMatches": readme_matches,
                  "readmeTextMatchesIgnoringTargets": readme_text_matches, "repositoryLinksWithParentSegments": parent_links,
                  "entrypointPresent": "extension/" + manifest["main"].removeprefix("./") in names,
                  "runtimeJsFiles": len(expected), "runtimeMismatches": mismatches,
                  "lineEndingsOnly": line_endings_only, "unexpectedRuntimeJs": sorted(archived - expected.keys()),
                  "developmentFiles": dev_files}
    result["passed"] = (result["manifestMatches"] and readme_text_matches and not parent_links and result["entrypointPresent"]
                        and not mismatches and not result["unexpectedRuntimeJs"] and not dev_files)
    return result


def main() -> int:
    """Audit one or more compiled extension folders and emit machine-readable evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extensions", type=Path, nargs="+")
    args = parser.parse_args()
    results = [audit(extension) for extension in args.extensions]
    print(json.dumps(results, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
