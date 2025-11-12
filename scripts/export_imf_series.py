#!/usr/bin/env python3
"""
Export IMF World Economic Outlook series metadata to a JSON mapping file.

The script reads the curated CSV located at ``data/imf_weo.csv`` and produces a
mapping of IMF series codes to their indicator descriptions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from karana.loaders.imf import _extract_base_codes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export IMF WEO indicator metadata to JSON."
    )
    project_root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--csv",
        type=Path,
        default=project_root / "data" / "imf_weo.csv",
        help="Path to the IMF WEO CSV (defaults to data/imf_weo.csv).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=project_root / "imf_series_descriptions.json",
        help="Destination JSON file path. Defaults to the project root.",
    )
    return parser.parse_args()


def collect_series(csv_path: Path) -> dict[str, str]:
    if not csv_path.exists():
        raise FileNotFoundError(f"IMF WEO dataset not found at {csv_path}")

    df = pd.read_csv(csv_path, usecols=["SERIES_CODE", "INDICATOR"])
    base_codes = _extract_base_codes(df["SERIES_CODE"])

    records = (
        pd.DataFrame({"code": base_codes, "indicator": df["INDICATOR"]})
        .dropna(subset=["code", "indicator"])
        .drop_duplicates(subset=["code"])
    )

    mapping = {
        str(row["code"]).strip(): str(row["indicator"]).strip()
        for _, row in records.iterrows()
        if str(row["code"]).strip() and str(row["indicator"]).strip()
    }

    return dict(sorted(mapping.items()))


def main() -> None:
    args = parse_args()
    mapping = collect_series(args.csv)

    if not mapping:
        raise SystemExit("No IMF series metadata could be extracted from the CSV.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(mapping, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Exported {len(mapping)} IMF series descriptions to {args.output}")


if __name__ == "__main__":
    main()

