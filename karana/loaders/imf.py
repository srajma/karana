from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Sequence, Tuple

import pandas as pd  # type: ignore

_DEFAULT_IMF_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "imf_weo.csv"
_SPECIAL_SERIES_FILES: Dict[str, Path] = {
    "NGDPDPC.A": Path(__file__).resolve().parents[2] / "data" / "imf_weo_ngdpdpc.csv"
}


class IMFChartLoaderError(RuntimeError):
    """Raised when requested IMF WEO series cannot be prepared."""


def load_imf_charts(
    *series_codes: str,
    data_path: str | Path | None = None,
    override_specials: bool = False,
) -> Dict[str, pd.DataFrame]:
    """
    Load IMF WEO series for every available country and convert them into karana datasets.

    Parameters
    ----------
    series_codes:
        Base IMF series codes (e.g. ``\"PPPGDP.A\"``). Country-prefixes are added
        automatically based on the dataset.
    data_path:
        Optional custom CSV path. Defaults to ``data/imf_weo.csv`` at the project root.

    Returns
    -------
    dict[str, pandas.DataFrame]
        Mapping of dataset keys to DataFrames ready for :class:`karana.LineGraph`. Keys
        take the form ``{code}[{indicator description}]``.
    """

    if not series_codes:
        raise ValueError("load_imf_charts requires at least one IMF series code.")

    datasets: "OrderedDict[str, pd.DataFrame]" = OrderedDict()
    general_info: Tuple[pd.DataFrame, pd.Series, Sequence[str]] | None = None
    special_info_cache: Dict[str, Tuple[pd.DataFrame, pd.Series, Sequence[str]]] = {}

    for code in series_codes:
        dataset: pd.DataFrame
        base_codes: pd.Series
        year_columns: Sequence[str]

        use_special = not override_specials and code in _SPECIAL_SERIES_FILES
        if use_special:
            if code not in special_info_cache:
                path = _SPECIAL_SERIES_FILES[code]
                dataset, base_codes, year_columns = _load_special_series(code, path)
                special_info_cache[code] = (dataset, base_codes, year_columns)
            dataset, base_codes, year_columns = special_info_cache[code]
        else:
            if general_info is None:
                dataset = _load_imf_dataset(data_path)
                base_codes = _extract_base_codes(dataset["SERIES_CODE"])
                year_columns = _year_columns(dataset.columns)
                if not year_columns:
                    raise IMFChartLoaderError("IMF dataset does not contain any year columns.")
                general_info = (dataset, base_codes, year_columns)
            dataset, base_codes, year_columns = general_info

        key, frame = _build_series_entry(dataset, base_codes, year_columns, code)
        datasets[key] = frame

    return datasets


def load_imf_ngdpdpc(
    *,
    data_path: str | Path | None = None,
    override_specials: bool = False,
) -> Dict[str, pd.DataFrame]:
    """
    Convenience helper to load the NGDPDPC.A series, using the curated special dataset
    unless ``override_specials`` is set.
    """

    if override_specials:
        return load_imf_charts("NGDPDPC.A", data_path=data_path, override_specials=True)

    path = Path(data_path) if data_path is not None else _SPECIAL_SERIES_FILES["NGDPDPC.A"]
    dataset, base_codes, year_columns = _load_special_series("NGDPDPC.A", path)
    key, frame = _build_series_entry(dataset, base_codes, year_columns, "NGDPDPC.A")
    return {key: frame}


def _year_columns(columns: Iterable[str]) -> Sequence[str]:
    years: list[str] = []
    for column in columns:
        if isinstance(column, str) and column.isdigit():
            years.append(column)
    years.sort()
    return years


def _extract_base_codes(code_series: pd.Series) -> pd.Series:
    expanded = code_series.astype(str).str.split(".", n=1, expand=True)
    if expanded.shape[1] == 1:
        return expanded[0]
    return expanded[1].fillna(expanded[0])


def _load_imf_dataset(data_path: str | Path | None) -> pd.DataFrame:
    path = Path(data_path) if data_path is not None else _DEFAULT_IMF_DATA_PATH
    if not path.exists():
        raise FileNotFoundError(f"IMF WEO dataset not found at {path}")
    return _cached_imf_dataset(path.resolve())


@lru_cache(maxsize=4)
def _cached_imf_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    required_columns = {"SERIES_CODE", "INDICATOR"}
    missing = required_columns - set(df.columns)
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise IMFChartLoaderError(
            f"IMF dataset at {path} missing required column(s): {missing_str}"
        )
    return df


def _build_series_entry(
    dataset: pd.DataFrame,
    base_codes: pd.Series,
    year_columns: Sequence[str],
    code: str,
) -> Tuple[str, pd.DataFrame]:
    mask = base_codes == code
    subset = dataset.loc[mask].copy()
    if subset.empty:
        raise IMFChartLoaderError(f"Series code '{code}' not found in IMF dataset.")

    indicator_values = subset["INDICATOR"].dropna().unique()
    if len(indicator_values) == 0:
        indicator_desc = "Unknown indicator"
    elif len(indicator_values) == 1:
        indicator_desc = indicator_values[0]
    else:
        raise IMFChartLoaderError(
            f"Series code '{code}' has inconsistent indicator descriptions."
        )

    frame = subset[["COUNTRY", *year_columns]].copy()
    frame.rename(columns={"COUNTRY": "Region"}, inplace=True)

    for column in year_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame.sort_values("Region", inplace=True)
    frame.reset_index(drop=True, inplace=True)

    key = f"{code}[{indicator_desc}]"
    return key, frame


@lru_cache(maxsize=4)
def _load_special_series(
    code: str,
    path: Path,
) -> Tuple[pd.DataFrame, pd.Series, Sequence[str]]:
    if not path.exists():
        raise FileNotFoundError(f"IMF special dataset for '{code}' not found at {path}")

    try:
        dataset = _cached_imf_dataset(path.resolve())
        base_codes = _extract_base_codes(dataset["SERIES_CODE"])
        year_columns = _year_columns(dataset.columns)
        if not year_columns:
            raise IMFChartLoaderError(
                f"IMF special dataset for '{code}' does not contain year columns."
            )
        return dataset, base_codes, year_columns
    except (IMFChartLoaderError, pd.errors.ParserError, KeyError):
        pass

    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line != ""]
    if len(lines) < 3:
        raise IMFChartLoaderError(
            f"IMF special dataset at {path} does not contain enough data rows."
        )

    indicator_raw = lines[0].strip('"')
    indicator_desc = " ".join(indicator_raw.split())

    year_tokens = [token.strip() for token in lines[1].split(",")]
    year_columns = [token for token in year_tokens if token.isdigit()]
    if not year_columns:
        raise IMFChartLoaderError(
            f"Could not determine year columns from IMF special dataset at {path}."
        )

    records: list[list[object]] = []
    for line in lines[2:]:
        if not line:
            continue
        parts = [part.strip() for part in line.split(",")]
        if not parts:
            continue
        country = parts[0]
        if not country:
            continue
        values = parts[1:]
        if len(values) < len(year_columns):
            values = values + [None] * (len(year_columns) - len(values))
        else:
            values = values[: len(year_columns)]
        normalized = [
            None if (isinstance(v, str) and v.lower() in {"no data", "na", ""}) else v
            for v in values
        ]
        records.append([country, *normalized])

    data = pd.DataFrame(records, columns=["COUNTRY", *year_columns])
    data.insert(0, "INDICATOR", indicator_desc)
    data.insert(0, "SERIES_CODE", [f"{code}" for _ in range(len(data))])
    base_codes = pd.Series([code] * len(data))

    return data, base_codes, year_columns


