#!/usr/bin/env python3
"""
Export World Bank series metadata to a JSON mapping file.

This script queries the World Bank API (via wbgapi) for all indicators in the
specified database and writes a mapping of indicator IDs to their human-readable
descriptions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, MutableMapping, Optional

import wbgapi as wb  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export World Bank indicator metadata to JSON."
    )
    parser.add_argument(
        "--database",
        "-d",
        type=int,
        default=2,
        help="World Bank database ID (defaults to 2: World Development Indicators).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "worldbank_series_descriptions.json",
        help="Destination JSON file path. Defaults to the project root.",
    )
    return parser.parse_args()


def _description_from_metadata(metadata: Mapping[str, object]) -> Optional[str]:
    candidates = ("value", "name", "label", "description")
    for key in candidates:
        if key in metadata:
            value = metadata[key]
            if isinstance(value, Mapping):
                nested = value.get("value") or value.get("name")
                if nested:
                    return str(nested).strip()
            elif value not in (None, ""):
                return str(value).strip()
    return None


def collect_series(database: int) -> dict[str, str]:
    mapping: MutableMapping[str, str] = {}
    for item in wb.series.list(db=database):  # type: ignore[arg-type]
        if not isinstance(item, Mapping):
            continue
        code = str(item.get("id") or "").strip()
        if not code:
            continue
        description = _description_from_metadata(item)
        if not description:
            # Fallback to asking for the full metadata, which can include the title
            try:
                meta = wb.series.get(code, db=database)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover - network failure
                meta = None
            if isinstance(meta, Mapping):
                description = _description_from_metadata(meta)
        if description:
            mapping[code] = description
    return dict(sorted(mapping.items()))


def main() -> None:
    args = parse_args()
    mapping = collect_series(args.database)

    if not mapping:
        raise SystemExit("No World Bank series metadata could be retrieved.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(mapping, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        f"Exported {len(mapping)} World Bank series descriptions to {args.output}"
    )


if __name__ == "__main__":
    main()

