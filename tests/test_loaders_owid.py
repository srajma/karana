from pathlib import Path

import pandas as pd  # type: ignore
import pytest  # type: ignore

from karana import LineGraph
from karana.loaders.owid import (
    OWIDChartLoaderError,
    _convert_tidy_chart,
    load_chart,
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
    assert set(datasets.keys()) == {"life_expectancy"}

    result = datasets["life_expectancy"]
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


@pytest.mark.integration
def test_load_chart_produces_html():
    try:
        datasets = load_chart("life-expectancy")
    except Exception as exc:  # pragma: no cover - best effort for flaky network
        pytest.skip(f"OWID chart fetch failed: {exc}")

    assert datasets, "Expected at least one dataset from OWID loader."

    graph = LineGraph(datasets)
    graph.default_df(next(iter(datasets)))

    output_path = PROJECT_ROOT / "owid_life_expectancy_test.html"
    graph.show(str(output_path))

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "life-expectancy" in content or "karana LineGraph" in content

