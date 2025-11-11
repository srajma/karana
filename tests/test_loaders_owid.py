from pathlib import Path

import pandas as pd  # type: ignore
import pytest  # type: ignore

from karana import LineGraph
from karana.loaders.owid import (
    OWIDChartLoaderError,
    _convert_tidy_chart,
    load_chart,
    load_charts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_convert_tidy_chart_single_column():
    tidy = pd.DataFrame(
        {
            "entities": ["Alpha", "Alpha", "Beta", "Beta"],
            "years": [2020, 2021, 2020, 2021],
            "life_expectancy": [65.0, 66.0, 70.0, 71.5],
        }
    )

    datasets = _convert_tidy_chart("life-expectancy", tidy)
    assert set(datasets.keys()) == {"life-expectancy:life_expectancy"}

    result = datasets["life-expectancy:life_expectancy"]
    expected = pd.DataFrame(
        {
            "Region": ["Alpha", "Beta"],
            "2020": [65.0, 70.0],
            "2021": [66.0, 71.5],
        }
    )

    pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


def test_convert_tidy_chart_multiple_columns_with_prefix():
    tidy = pd.DataFrame(
        {
            "entities": ["Alpha", "Alpha", "Beta", "Beta"],
            "years": [2020, 2021, 2020, 2021],
            "gdp": [1500.0, 1600.0, 2100.0, 2200.0],
            "population": [1.5, 1.55, 2.0, 2.05],
            "note": ["x", "y", "z", "w"],
        }
    )

    datasets = _convert_tidy_chart(
        "economy",
        tidy,
        value_columns=["gdp", "population"],
        key_prefix="economy",
    )

    assert list(datasets.keys()) == ["economy:gdp", "economy:population"]
    for frame in datasets.values():
        assert frame.columns[0] == "Region"
        assert list(frame.columns[1:]) == ["2020", "2021"]


def test_convert_tidy_chart_missing_required_columns():
    tidy = pd.DataFrame({"years": [2020], "value": [1.0]})

    with pytest.raises(OWIDChartLoaderError):
        _convert_tidy_chart("broken", tidy)


def test_load_charts_combines_multiple(monkeypatch):
    slug_data = {
        "chart_a": pd.DataFrame(
            {
                "entities": ["Alpha", "Beta"],
                "years": [2020, 2020],
                "value_a": [1.0, 2.0],
            }
        ),
        "chart_b": pd.DataFrame(
            {
                "entities": ["Alpha", "Beta"],
                "years": [2020, 2020],
                "value_b": [3.0, 4.0],
            }
        ),
    }

    monkeypatch.setattr(
        "karana.loaders.owid.charts.get_data",
        lambda slug: slug_data[slug],
    )

    datasets = load_charts(
        "chart_a",
        "chart_b",
        value_columns={"chart_a": ["value_a"], "chart_b": ["value_b"]},
        key_prefix={"chart_a": "a", "chart_b": "b"},
        use_cache=False,
    )

    assert set(datasets) == {"a:value_a", "b:value_b"}
    for df in datasets.values():
        assert list(df.columns) == ["Region", "2020"]


def test_load_charts_detects_key_collisions(monkeypatch):
    df = pd.DataFrame(
        {
            "entities": ["Alpha"],
            "years": [2020],
            "value": [1.0],
        }
    )

    monkeypatch.setattr(
        "karana.loaders.owid.charts.get_data",
        lambda slug: df,
    )

    with pytest.raises(OWIDChartLoaderError):
        load_charts(
            "chart_a",
            "chart_b",
            value_columns=["value"],
            key_prefix="shared",
            use_cache=False,
        )


def test_load_charts_default_slug_prefix(monkeypatch):
    slug_data = {
        "chart_a": pd.DataFrame(
            {
                "entities": ["Alpha"],
                "years": [2020],
                "value": [1.0],
            }
        ),
        "chart_b": pd.DataFrame(
            {
                "entities": ["Beta"],
                "years": [2020],
                "value": [2.0],
            }
        ),
    }

    monkeypatch.setattr(
        "karana.loaders.owid.charts.get_data",
        lambda slug: slug_data[slug],
    )

    datasets = load_charts(
        "chart_a",
        "chart_b",
        value_columns=["value"],
        use_cache=False,
    )

    assert set(datasets.keys()) == {"chart_a:value", "chart_b:value"}


def test_load_chart_uses_cache(monkeypatch, tmp_path):
    tidy = pd.DataFrame(
        {
            "entities": ["Alpha"],
            "years": [2020],
            "value": [1.0],
        }
    )
    calls: list[str] = []

    def fake_get_data(slug: str) -> pd.DataFrame:
        calls.append(slug)
        return tidy

    monkeypatch.setattr("karana.loaders.owid.charts.get_data", fake_get_data)

    cache_dir = tmp_path / "cache"

    load_chart("cached-chart", value_columns=["value"], cache_dir=cache_dir)
    assert calls == ["cached-chart"]
    cache_file = cache_dir / "cached-chart.feather"
    assert cache_file.exists()

    calls.clear()
    load_chart("cached-chart", value_columns=["value"], cache_dir=cache_dir)
    assert calls == []


@pytest.mark.integration
def test_load_chart_produces_html():

    india_administrations = [
        {"start": 1947, "end": 1964, "PM": "Nehru", "party": "INC", "color": "#00AEEF"},
        {"start": 1964, "end": 1966, "PM": "Shastri", "party": "INC", "color": "#00AEEF"},
        {"start": 1966, "end": 1977, "PM": "Indira Gandhi", "party": "INC", "color": "#00AEEF"},
        {"start": 1977, "end": 1979, "PM": "Desai", "party": "JP", "color": "#FFC105"},
        {"start": 1979, "end": 1980, "PM": "Charan Singh", "party": "JP (S)", "color": "#FFC105"},
        {"start": 1980, "end": 1984, "PM": "Indira Gandhi", "party": "INC", "color": "#00AEEF"},
        {"start": 1984, "end": 1989, "PM": "Rajiv Gandhi", "party": "INC", "color": "#00AEEF"},
        {"start": 1989, "end": 1990, "PM": "VP Singh", "party": "JD", "color": "#FFC105"},
        {"start": 1990, "end": 1991, "PM": "Chandra Shekhar", "party": "SJP", "color": "#999999"},
        {"start": 1991, "end": 1996, "PM": "P.V. Narasimha Rao", "party": "INC", "color": "#00AEEF"},
        {"start": 1996, "end": 1997, "PM": "Deve Gowda", "party": "JD", "color": "#FFC105"},
        {"start": 1997, "end": 1998, "PM": "Gujral", "party": "JD", "color": "#FFC105"},
        {"start": 1998, "end": 2004, "PM": "Vajpayee", "party": "BJP", "color": "#FF7518"},
        {"start": 2004, "end": 2014, "PM": "Rg. Sonia Gandhi", "party": "INC", "color": "#00AEEF"},
        {"start": 2014, "end": 2024, "PM": "Narendra Modi", "party": "BJP", "color": "#FF7518"}
    ]

    try:
        datasets = load_chart("life-expectancy")
    except Exception as exc:  # pragma: no cover - best effort for flaky network
        pytest.skip(f"OWID chart fetch failed: {exc}")

    assert datasets, "Expected at least one dataset from OWID loader."

    graph = LineGraph(datasets)
    graph.default_df(next(iter(datasets)))
    graph.administrations(india_administrations)

    output_path = PROJECT_ROOT / "owid_life_expectancy_test.html"
    graph.show(str(output_path))

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "life-expectancy" in content or "karana LineGraph" in content

