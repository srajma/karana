from pathlib import Path

import pandas as pd  # type: ignore
import pytest  # type: ignore

from karana.loaders.imf import IMFChartLoaderError, load_imf_charts


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
    assert gdp.iloc[0]["Region"] == "IND.PPPGDP.A"
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

