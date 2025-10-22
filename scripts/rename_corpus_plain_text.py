#!/usr/bin/env python
"""
Rename the `full_text_abstract` field to `plain_text` across corpus JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


def iter_json_files(root: Path) -> Iterable[Path]:
    """
    Yield JSON files located directly under the provided root directory.
    """
    yield from root.glob("*.json")


def rename_key(path: Path, *, dry_run: bool = False) -> bool:
    """
    Rename `full_text_abstract` -> `plain_text` inside a single JSON file.

    Returns:
        True when a change was (or would be) made, False otherwise.
    """
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict) or "full_text_abstract" not in data:
        return False

    new_value = data.pop("full_text_abstract")
    data["plain_text"] = new_value

    if dry_run:
        return True

    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    return True


if __name__ == "__main__":
    updated = 0
    checked = 0
    corpus_dir = Path("./data/corpus/")
    files = list(iter_json_files(corpus_dir))
    print(f"Found {len(files)} files to process.")
    for file in files:
        checked += 1
        if rename_key(file, dry_run=False):
            updated += 1
            print(f"[DRY RUN] Renamed key in {file}")

    print(f"Processed {checked} files; would update {updated}.")
