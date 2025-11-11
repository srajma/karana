from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Sequence

import pandas as pd  # type: ignore

_DEFAULT_IMF_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "imf_weo.csv"


class IMFChartLoaderError(RuntimeError):
    """Raised when requested IMF WEO series cannot be prepared."""


def load_imf_charts(
    *series_codes: str,
    data_path: str | Path | None = None,
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

    dataset = _load_imf_dataset(data_path)
    base_codes = _extract_base_codes(dataset["SERIES_CODE"])
    year_columns = _year_columns(dataset.columns)

    if not year_columns:
        raise IMFChartLoaderError("IMF dataset does not contain any year columns.")

    datasets: "OrderedDict[str, pd.DataFrame]" = OrderedDict()

    for code in series_codes:
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

        frame = subset[["SERIES_CODE", *year_columns]].copy()
        frame.rename(columns={"SERIES_CODE": "Region"}, inplace=True)

        for column in year_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        frame.sort_values("Region", inplace=True)
        frame.reset_index(drop=True, inplace=True)

        key = f"{code}[{indicator_desc}]"
        datasets[key] = frame

    return datasets


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


