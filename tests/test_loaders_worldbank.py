from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore
import pytest  # type: ignore

from karana.loaders.worldbank import (
    WorldBankLoaderError,
    load_worldbank_series,
)


def test_load_worldbank_series_transforms_to_wide(monkeypatch):
    indicator = "NY.GDP.PCAP.CD"

    def fake_fetch(
        code: str,
        economies: Any,
        time: Any,
        **options: Any,
    ):
        assert code == indicator
        assert economies == ["IND", "USA"]
        assert list(time) == [2020, 2021]
        return [
            {"economy": "India", "time": 2020, indicator: "1234.5"},
            {"economy": "India", "time": 2021, indicator: 1300.0},
            {
                "economy": {"id": "USA", "value": "United States"},
                "time": "2020",
                indicator: "5678.9",
            },
            {
                "economy": {"id": "USA", "value": "United States"},
                "time": "2021",
                indicator: None,
            },
        ]

    def fake_series_get(code: str, db: Any = None):
        assert code == indicator
        assert db == 2
        return {"value": "GDP per capita (current US$)"}

    monkeypatch.setattr(
        "karana.loaders.worldbank.wb.data.fetch",
        fake_fetch,
    )
    monkeypatch.setattr(
        "karana.loaders.worldbank.wb.series.get",
        fake_series_get,
    )

    datasets = load_worldbank_series(
        indicator,
        economies=["IND", "USA"],
        time=[2020, 2021],
        database=2,
    )

    expected_key = "NY.GDP.PCAP.CD[GDP per capita (current US$)]"
    assert list(datasets) == [expected_key]

    frame = datasets[expected_key]
    assert list(frame.columns) == ["Region", "2020", "2021"]
    assert list(frame["Region"]) == ["India", "United States"]
    assert pytest.approx(frame.loc[frame["Region"] == "India", "2020"].item()) == 1234.5
    assert pytest.approx(frame.loc[frame["Region"] == "India", "2021"].item()) == 1300.0
    usa_2021 = frame.loc[frame["Region"] == "United States", "2021"].item()
    assert pd.isna(usa_2021)


def test_load_worldbank_series_respects_fetch_overrides(monkeypatch):
    indicator = "SP.POP.TOTL"
    calls: list[dict[str, Any]] = []

    def fake_fetch(code: str, economies: Any, time: Any, **options: Any):
        calls.append({"code": code, "economies": economies, "time": time, "options": options})
        return [
            {"economy": "India", "time": 2020, indicator: 1_380_004_385},
        ]

    monkeypatch.setattr(
        "karana.loaders.worldbank.wb.data.fetch",
        fake_fetch,
    )
    monkeypatch.setattr(
        "karana.loaders.worldbank.wb.series.get",
        lambda *args, **kwargs: {},
    )

    datasets = load_worldbank_series(
        indicator,
        most_recent=5,
        database=4,
        gapfill=True,
        frequency="A",
        fetch_options={"mrv": 2, "mrnev": 3},
    )

    assert indicator in datasets
    assert len(calls) == 1

    call = calls[0]
    assert call["code"] == indicator
    assert call["economies"] == "all"
    assert call["time"] == "all"

    options = call["options"]
    assert options["db"] == 4
    assert options["labels"] is True
    assert options["gapfill"] is True
    assert options["freq"] == "A"
    assert options["mrnev"] == 3
    assert options["mrv"] == 2  # fetch_options override takes precedence


def test_load_worldbank_series_no_observations_raises(monkeypatch):
    monkeypatch.setattr(
        "karana.loaders.worldbank.wb.data.fetch",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "karana.loaders.worldbank.wb.series.get",
        lambda *args, **kwargs: {},
    )

    with pytest.raises(WorldBankLoaderError):
        load_worldbank_series("NY.GDP.MKTP.CD")


