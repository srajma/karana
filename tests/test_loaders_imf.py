from pathlib import Path

import pandas as pd  # type: ignore
import pytest  # type: ignore

import karana.loaders.imf as imf_module
from karana.loaders.imf import (
    IMFChartLoaderError,
    load_imf_charts,
    load_imf_ngdpdpc,
)


def test_load_imf_charts_filters_and_formats(tmp_path):
    data = pd.DataFrame(
        {
            "SERIES_CODE": [
                "IND.PPPGDP.A",
                "USA.PPPGDP.A",
                "IND.PPPPC.A",
                "USA.PPPPC.A",
            ],
            "INDICATOR": [
                "GDP PPP dollars",
                "GDP PPP dollars",
                "GDP per capita PPP dollars",
                "GDP per capita PPP dollars",
            ],
            "COUNTRY": ["India", "United States", "India", "United States"],
            "2020": ["123.4", "567.8", "1.2", "3.4"],
            "2021": ["125.0", "580.0", "1.3", "3.5"],
        }
    )
    csv_path = tmp_path / "imf.csv"
    data.to_csv(csv_path, index=False)

    datasets = load_imf_charts("PPPGDP.A", "PPPPC.A", data_path=csv_path)

    assert set(datasets) == {
        "PPPGDP.A[GDP PPP dollars]",
        "PPPPC.A[GDP per capita PPP dollars]",
    }

    gdp = datasets["PPPGDP.A[GDP PPP dollars]"]
    assert list(gdp.columns) == ["Region", "2020", "2021"]
    assert list(gdp["Region"]) == ["India", "United States"]
    assert pytest.approx(gdp.iloc[0]["2020"]) == 123.4
    assert pytest.approx(gdp.iloc[1]["2021"]) == 580.0


def test_load_imf_charts_missing_series_raises(tmp_path):
    data = pd.DataFrame(
        {
            "SERIES_CODE": ["IND.PPPGDP.A"],
            "INDICATOR": ["GDP PPP dollars"],
            "COUNTRY": ["India"],
            "2020": [100.0],
        }
    )
    csv_path = tmp_path / "imf.csv"
    data.to_csv(csv_path, index=False)

    with pytest.raises(IMFChartLoaderError):
        load_imf_charts("PPPPC.A", data_path=csv_path)


def test_load_imf_charts_default_path_exists():
    default_path = Path(__file__).resolve().parents[1] / "data" / "imf_weo.csv"
    assert default_path.exists()


def test_load_imf_charts_uses_special_dataset(monkeypatch, tmp_path):
    general_data = pd.DataFrame(
        {
            "SERIES_CODE": ["IND.NGDPDPC.A", "USA.NGDPDPC.A"],
            "INDICATOR": ["General GDP", "General GDP"],
            "COUNTRY": ["India", "United States"],
            "2020": [100.0, 200.0],
        }
    )
    special_data = pd.DataFrame(
        {
            "SERIES_CODE": ["IND.NGDPDPC.A", "USA.NGDPDPC.A"],
            "INDICATOR": ["Special GDP", "Special GDP"],
            "COUNTRY": ["India", "United States"],
            "2020": [110.0, 210.0],
        }
    )

    general_path = tmp_path / "general.csv"
    special_path = tmp_path / "special.csv"
    general_data.to_csv(general_path, index=False)
    special_data.to_csv(special_path, index=False)

    monkeypatch.setattr(imf_module, "_DEFAULT_IMF_DATA_PATH", general_path)
    monkeypatch.setitem(imf_module._SPECIAL_SERIES_FILES, "NGDPDPC.A", special_path)
    imf_module._cached_imf_dataset.cache_clear()

    datasets = load_imf_charts("NGDPDPC.A", data_path=general_path)
    key = next(iter(datasets))
    assert key.startswith("NGDPDPC.A[Special GDP]")
    df = datasets[key]
    assert list(df["Region"]) == ["India", "United States"]
    assert pytest.approx(df.iloc[0]["2020"]) == 110.0


def test_load_imf_charts_override_special(monkeypatch, tmp_path):
    general_data = pd.DataFrame(
        {
            "SERIES_CODE": ["IND.NGDPDPC.A", "USA.NGDPDPC.A"],
            "INDICATOR": ["General GDP", "General GDP"],
            "COUNTRY": ["India", "United States"],
            "2020": [120.0, 220.0],
        }
    )
    special_data = pd.DataFrame(
        {
            "SERIES_CODE": ["IND.NGDPDPC.A", "USA.NGDPDPC.A"],
            "INDICATOR": ["Special GDP", "Special GDP"],
            "COUNTRY": ["India", "United States"],
            "2020": [130.0, 230.0],
        }
    )

    general_path = tmp_path / "general.csv"
    special_path = tmp_path / "special.csv"
    general_data.to_csv(general_path, index=False)
    special_data.to_csv(special_path, index=False)

    monkeypatch.setattr(imf_module, "_DEFAULT_IMF_DATA_PATH", general_path)
    monkeypatch.setitem(imf_module._SPECIAL_SERIES_FILES, "NGDPDPC.A", special_path)
    imf_module._cached_imf_dataset.cache_clear()

    datasets = load_imf_charts(
        "NGDPDPC.A",
        data_path=general_path,
        override_specials=True,
    )
    key = next(iter(datasets))
    assert key.startswith("NGDPDPC.A[General GDP]")
    df = datasets[key]
    assert pytest.approx(df.iloc[0]["2020"]) == 120.0


def test_load_imf_ngdpdpc_helper(monkeypatch, tmp_path):
    special_data = pd.DataFrame(
        {
            "SERIES_CODE": ["IND.NGDPDPC.A"],
            "INDICATOR": ["Special GDP"],
            "COUNTRY": ["India"],
            "2020": [140.0],
        }
    )
    special_path = tmp_path / "special.csv"
    special_data.to_csv(special_path, index=False)

    monkeypatch.setitem(imf_module._SPECIAL_SERIES_FILES, "NGDPDPC.A", special_path)
    imf_module._cached_imf_dataset.cache_clear()

    datasets = load_imf_ngdpdpc()
    key = next(iter(datasets))
    assert key.startswith("NGDPDPC.A[Special GDP]")
    assert pytest.approx(datasets[key].iloc[0]["2020"]) == 140.0

    general_data = pd.DataFrame(
        {
            "SERIES_CODE": ["IND.NGDPDPC.A"],
            "INDICATOR": ["General GDP"],
            "COUNTRY": ["India"],
            "2020": [150.0],
        }
    )
    general_path = tmp_path / "general.csv"
    general_data.to_csv(general_path, index=False)

    datasets_override = load_imf_ngdpdpc(
        data_path=general_path,
        override_specials=True,
    )
    key_override = next(iter(datasets_override))
    assert key_override.startswith("NGDPDPC.A[General GDP]")
    assert pytest.approx(datasets_override[key_override].iloc[0]["2020"]) == 150.0


def test_special_dataset_without_metadata(monkeypatch, tmp_path):
    content = "\n".join(
        [
            "\"GDP per capita\"", "1980,1981,1982",
            ",,,",
            "India,100,110,120",
            "United States,200,210,220",
        ]
    )
    special_path = tmp_path / "special.csv"
    special_path.write_text(content, encoding="utf-8")

    monkeypatch.setitem(imf_module._SPECIAL_SERIES_FILES, "NGDPDPC.A", special_path)
    imf_module._cached_imf_dataset.cache_clear()
    imf_module._load_special_series.cache_clear()

    datasets = load_imf_charts("NGDPDPC.A")
    key = next(iter(datasets))
    assert key.startswith("NGDPDPC.A[GDP per capita]")
    df = datasets[key]
    assert list(df["Region"]) == ["India", "United States"]

