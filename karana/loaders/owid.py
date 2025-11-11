from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence

import pandas as pd  # type: ignore
from owid.catalog import charts  # type: ignore


_DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "owid"


class OWIDChartLoaderError(RuntimeError):
    """Raised when an OWID chart cannot be transformed into the expected format."""


def load_chart(
    slug: str,
    *,
    value_columns: Iterable[str] | None = None,
    key_prefix: str | None = None,
    use_cache: bool = True,
    cache_dir: Path | None = None,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch a chart dataset from OWID and convert it into karana's wide-table format.

    Parameters
    ----------
    slug:
        Chart identifier as used on Our World In Data (e.g. ``life-expectancy``).
    value_columns:
        Optional subset of columns to keep from the tidy OWID table. If omitted, all
        numeric value columns (excluding ``entities`` and ``years``) are converted.
    key_prefix:
        Optional prefix used for the resulting dataset keys. Helpful when combining
        multiple charts to avoid name collisions. If not provided the raw column name
        is used. When multiple columns are transformed and ``key_prefix`` is omitted,
        the keys will take the form ``{slug}:{column}``.

    Returns
    -------
    dict[str, pandas.DataFrame]
        Mapping from dataset identifier to a DataFrame with columns ``Region`` and one
        column per year, suited for :class:`karana.LineGraph`.
    """

    tidy = _load_tidy_chart(slug, use_cache=use_cache, cache_dir=cache_dir)
    return _convert_tidy_chart(
        slug,
        tidy,
        value_columns=value_columns,
        key_prefix=key_prefix,
    )


def load_charts(
    *slugs: str,
    value_columns: Mapping[str, Iterable[str]] | Iterable[str] | None = None,
    key_prefix: Mapping[str, str] | str | None = None,
    use_cache: bool = True,
    cache_dir: Path | None = None,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch multiple OWID charts and combine their datasets.

    Parameters
    ----------
    slugs:
        One or more chart identifiers (e.g. ``\"life-expectancy\"``).
    value_columns:
        Either a universal iterable of column names applied to every slug, or a mapping
        from slug to its specific iterable of columns. When omitted, each chart infers
        its own numeric value columns.
    key_prefix:
        Either a universal prefix applied to dataset keys or a mapping from slug to
        prefix. Allows namespace customization per chart.

    Returns
    -------
    dict[str, pandas.DataFrame]
        Combined mapping suitable for :class:`karana.LineGraph`.
    """

    if not slugs:
        raise ValueError("load_charts requires at least one chart slug.")

    datasets: "OrderedDict[str, pd.DataFrame]" = OrderedDict()

    for slug in slugs:
        columns = (
            value_columns.get(slug)
            if isinstance(value_columns, Mapping)
            else value_columns
        )
        prefix = key_prefix.get(slug) if isinstance(key_prefix, Mapping) else key_prefix

        slug_datasets = load_chart(
            slug,
            value_columns=columns,
            key_prefix=prefix,
            use_cache=use_cache,
            cache_dir=cache_dir,
        )

        overlap = set(datasets).intersection(slug_datasets)
        if overlap:
            overlap_str = ", ".join(sorted(overlap))
            raise OWIDChartLoaderError(
                f"Dataset key collision when loading chart '{slug}': {overlap_str}"
            )

        datasets.update(slug_datasets)

    return datasets


def _load_tidy_chart(
    slug: str,
    *,
    use_cache: bool,
    cache_dir: Path | None,
) -> pd.DataFrame:
    cache_root = cache_dir or _DEFAULT_CACHE_DIR
    cache_path = cache_root / f"{slug}.feather"

    if use_cache and cache_path.exists():
        return pd.read_feather(cache_path)

    tidy = charts.get_data(slug)

    if use_cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tidy.reset_index(drop=True).to_feather(cache_path)

    return tidy


def _convert_tidy_chart(
    slug: str,
    tidy: pd.DataFrame,
    *,
    value_columns: Iterable[str] | None = None,
    key_prefix: str | None = None,
) -> Dict[str, pd.DataFrame]:
    if "entities" not in tidy.columns or "years" not in tidy.columns:
        missing = {"entities", "years"} - set(tidy.columns)
        raise OWIDChartLoaderError(
            f"Chart '{slug}' is missing required column(s): {', '.join(sorted(missing))}."
        )

    candidate_columns: Sequence[str]
    if value_columns is None:
        candidate_columns = _infer_value_columns(tidy)
    else:
        candidate_columns = list(value_columns)
        missing = [col for col in candidate_columns if col not in tidy.columns]
        if missing:
            missing_str = ", ".join(missing)
            raise OWIDChartLoaderError(
                f"Requested columns not present in chart '{slug}': {missing_str}"
            )

    if not candidate_columns:
        raise OWIDChartLoaderError(
            f"Chart '{slug}' does not contain any usable numeric value columns."
        )

    datasets: "OrderedDict[str, pd.DataFrame]" = OrderedDict()
    base_prefix = key_prefix or slug

    for column in candidate_columns:
        wide = _tidy_column_to_wide(tidy, column)

        key = f"{base_prefix}:{column}"

        datasets[key] = wide

    return datasets


def _infer_value_columns(tidy: pd.DataFrame) -> Sequence[str]:
    reserved = {"entities", "years", "entity_ids", "entity_codes"}
    numeric_columns = [
        col
        for col in tidy.columns
        if col not in reserved and pd.api.types.is_numeric_dtype(tidy[col])
    ]
    return numeric_columns


def _tidy_column_to_wide(tidy: pd.DataFrame, value_column: str) -> pd.DataFrame:
    subset = tidy[["entities", "years", value_column]].copy()
    subset = subset.dropna(subset=["entities", "years"])

    subset["years"] = subset["years"].apply(_normalize_year)
    subset[value_column] = pd.to_numeric(subset[value_column], errors="coerce")

    wide = subset.pivot_table(
        index="entities",
        columns="years",
        values=value_column,
        aggfunc="first",
    )

    wide = wide.sort_index(axis=0)
    wide = wide.sort_index(axis=1)
    wide = wide.reset_index()
    wide = wide.rename(columns={"entities": "Region"})

    # Ensure consistent string labels for year columns.
    renamed_columns = ["Region"] + [str(col) for col in wide.columns[1:]]
    wide.columns = renamed_columns
    return wide


def _normalize_year(value: object) -> int:
    if isinstance(value, (int,)):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            numeric = float(value)
        except ValueError as exc:
            raise OWIDChartLoaderError(
                f"Unable to parse year value '{value}'."
            ) from exc
        return _normalize_year(numeric)
    raise OWIDChartLoaderError(f"Year values must be numeric convertible, got {value!r}.")

