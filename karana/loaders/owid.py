from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, Sequence

import pandas as pd  # type: ignore
from owid.catalog import charts


class OWIDChartLoaderError(RuntimeError):
    """Raised when an OWID chart cannot be transformed into the expected format."""


def load_chart(
    slug: str,
    *,
    value_columns: Iterable[str] | None = None,
    key_prefix: str | None = None,
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

    tidy = charts.get_data(slug)
    return _convert_tidy_chart(
        slug,
        tidy,
        value_columns=value_columns,
        key_prefix=key_prefix,
    )


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
    multi_column = len(candidate_columns) > 1

    for column in candidate_columns:
        wide = _tidy_column_to_wide(tidy, column)

        if key_prefix is not None:
            key = f"{key_prefix}:{column}"
        elif multi_column:
            key = f"{slug}:{column}"
        else:
            key = key_prefix or column

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

