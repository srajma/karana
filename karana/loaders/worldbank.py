from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, Mapping, Sequence

import pandas as pd  # type: ignore
import wbgapi as wb  # type: ignore


class WorldBankLoaderError(RuntimeError):
    """Raised when World Bank datasets cannot be transformed into karana format."""


def load_worldbank_series(
    *indicator_codes: str,
    economies: Iterable[str] | str | None = None,
    time: Sequence[int] | range | str | None = None,
    database: int | str | None = None,
    most_recent: int | None = None,
    labels: bool = True,
    gapfill: bool | None = None,
    frequency: str | None = None,
    fetch_options: Mapping[str, object] | None = None,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch World Bank indicators and convert them into karana's wide-table format.

    Parameters
    ----------
    indicator_codes:
        One or more World Bank indicator identifiers (e.g. ``\"NY.GDP.PCAP.CD\"``).
    economies:
        Iterable of economy identifiers accepted by the World Bank API. Defaults to
        ``\"all\"`` when omitted.
    time:
        Either ``\"all\"`` (default), a sequence of years, or a range compatible with the
        World Bank API ``time`` argument.
    database:
        Optional World Bank database identifier (``db`` in WBGAPI terminology).
    most_recent:
        Optional ``mrv`` argument limiting results to the most recent ``n`` observations.
    labels:
        Whether to request human-readable economy labels from the API. Defaults to True.
    gapfill:
        Optional ``gapfill`` parameter controlling interpolation of missing years.
    frequency:
        Optional ``freq`` parameter forwarded to the API (e.g. ``\"M\"`` for monthly).
    fetch_options:
        Additional keyword arguments forwarded directly to :func:`wbgapi.data.fetch`.

    Returns
    -------
    dict[str, pandas.DataFrame]
        Mapping from indicator keys to DataFrames ready for :class:`karana.LineGraph`.
        Each DataFrame contains a ``Region`` column followed by one column per year.
    """

    if not indicator_codes:
        raise ValueError("load_worldbank_series requires at least one indicator code.")

    economies_param = economies if economies is not None else "all"
    time_param = time if time is not None else "all"

    base_options: dict[str, object] = dict(fetch_options or {})
    if database is not None:
        base_options.setdefault("db", database)
    if most_recent is not None:
        base_options.setdefault("mrv", most_recent)
    if gapfill is not None:
        base_options.setdefault("gapfill", gapfill)
    if frequency is not None:
        base_options.setdefault("freq", frequency)
    if labels is not None:
        base_options.setdefault("labels", labels)

    datasets: "OrderedDict[str, pd.DataFrame]" = OrderedDict()

    for indicator in indicator_codes:
        options = dict(base_options)

        try:
            rows = list(
                wb.data.fetch(
                    indicator,
                    economies_param,
                    time_param,
                    **options,
                )
            )
        except Exception as exc:  # pragma: no cover - network/HTTP issues
            raise WorldBankLoaderError(
                f"Failed to load World Bank indicator '{indicator}'."
            ) from exc

        if not rows:
            raise WorldBankLoaderError(
                f"World Bank indicator '{indicator}' returned no observations."
            )

        records = []
        for row in rows:
            region = _extract_label(row, "economy")
            year = _extract_label(row, "time")
            value = row.get(indicator)

            numeric = _to_numeric(value)
            if numeric is None:
                continue

            records.append({"Region": region, "Year": year, "Value": numeric})

        if not records:
            raise WorldBankLoaderError(
                f"World Bank indicator '{indicator}' does not contain numeric values."
            )

        frame = pd.DataFrame.from_records(records)
        frame["Year"] = frame["Year"].apply(_normalize_year_string)

        pivot = (
            frame.pivot_table(
                index="Region",
                columns="Year",
                values="Value",
                aggfunc="first",
            )
            .sort_index(axis=0)
            .sort_index(axis=1)
        )
        pivot = pivot.reset_index()
        pivot.columns = ["Region", *[str(col) for col in pivot.columns[1:]]]

        key = _build_indicator_key(indicator, database)
        datasets[key] = pivot

    return datasets


def _extract_label(row: Mapping[str, object], field: str) -> str:
    if field not in row:
        raise WorldBankLoaderError(
            f"World Bank response is missing required field '{field}'."
        )

    value = row[field]
    if isinstance(value, Mapping):
        for candidate in ("value", "name", "label", "id"):
            if candidate in value and value[candidate] not in (None, ""):
                return str(value[candidate])
        raise WorldBankLoaderError(
            f"Could not determine label for field '{field}' from mapping {value!r}."
        )

    if value is None:
        raise WorldBankLoaderError(
            f"World Bank response returned null for required field '{field}'."
        )

    return str(value)


def _normalize_year_string(value: object) -> str:
    if isinstance(value, (int,)):
        return str(value)
    if isinstance(value, float):
        if pd.isna(value):
            raise WorldBankLoaderError("Encountered NaN year value in World Bank data.")
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return stripped
        try:
            numeric = float(stripped)
        except ValueError:
            return stripped
        if numeric.is_integer():
            return str(int(numeric))
        return str(numeric)
    raise WorldBankLoaderError(f"Unsupported year value type: {value!r}.")


def _to_numeric(value: object) -> float | None:
    if value in (None, "", ".."):
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in {"", ".."}:
            return None
        try:
            numeric = float(stripped)
        except ValueError:
            return None
        return numeric
    return None


def _build_indicator_key(indicator: str, database: int | str | None) -> str:
    try:
        metadata = wb.series.get(indicator, db=database)  # type: ignore[arg-type]
    except Exception:  # pragma: no cover - network/HTTP issues
        metadata = None

    description: str | None = None
    if isinstance(metadata, Mapping):
        for candidate in ("value", "name", "label"):
            meta_value = metadata.get(candidate)
            if isinstance(meta_value, Mapping):
                meta_value = meta_value.get("value") or meta_value.get("name")
            if meta_value:
                description = str(meta_value).strip()
                break

    if description:
        normalized = " ".join(description.split())
        return f"{indicator}[{normalized}]"
    return indicator


