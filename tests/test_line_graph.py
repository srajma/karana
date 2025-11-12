import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # type: ignore  # noqa: E402

from karana import LineGraph, Plot, series, show  # noqa: E402


def test_line_graph_generates_html():
    df = pd.DataFrame(
        {
            "Region": ["India", "World", "China"],
            2012: [np.nan, np.nan, np.nan],
            2013: [np.nan, np.nan, np.nan],
            2014: [np.nan, np.nan, np.nan],
            2015: [90, 180, 120],
            2016: [100, 200, 140],
            2017: [110, 220, 160],
            2018: [120, 240, 180],
            2019: [np.nan, 260, np.nan],
            2020: [np.nan, np.nan, np.nan],
        }
    )

    chart = LineGraph({"gdp_ppp": df})
    chart.default_df("gdp_ppp")
    chart.default_exp(
        series("India") / series("World"),
        series("China") / series("World"),
    )
    chart.default_scale("log")
    chart.administrations(
        [
            {
                "start": 2018,
                "end": 2019,
                "label": "Sample Admin",
                "party": "Test Party",
                "color": "#123456",
            }
        ]
    )

    output_file = PROJECT_ROOT / "test_outputs" / "test_line_graph_output.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    chart.show(str(output_file))

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "<title>gdp_ppp</title>" in content
    assert "payload =" in content
    assert "+ Add Expression" in content
    assert "Remove series" in content or "Remove expression" in content
    assert "Sample Admin" in content
    assert "Administrations" in content
    assert "admin-legend-item" in content
    assert "xAxisConfig.range = [xRangeMin, xRangeMax];" in content
    assert 'id="log-scale-toggle"' in content
    assert '"scale": "log"' in content


def test_default_df_accepts_slug_prefix():
    df = pd.DataFrame(
        {
            "Region": ["Alpha", "Beta"],
            "2020": [1.0, 2.0],
        }
    )
    chart = LineGraph({"terrorism-deaths:total_killed": df})

    chart.default_df("terrorism-deaths")

    assert chart._default_df == "terrorism-deaths:total_killed"


def test_plot_renders_multiple_graphs(tmp_path):
    df = pd.DataFrame(
        {
            "Region": ["Alpha", "Beta"],
            "2000": [10, 20],
            "2001": [12, 24],
            "2002": [14, 28],
        }
    )

    graph_one = LineGraph({"dataset_one": df})
    graph_one.default_df("dataset_one")
    graph_one.default_exp(series("Alpha"))

    graph_two = LineGraph({"dataset_two": df})
    graph_two.default_df("dataset_two")
    graph_two.default_exp(series("Beta"))

    plot = Plot("Example Plot")
    plot.add(graph_one)
    plot.html("<p class='note'>Between the charts</p>")
    plot.add(graph_two)

    output_file = tmp_path / "plot.html"
    plot.show(str(output_file))

    assert output_file.exists()
    html = output_file.read_text(encoding="utf-8")
    assert html.count("<iframe") == 2
    assert "Between the charts" in html
    assert "Example Plot" in html

    second_file = tmp_path / "plot_via_helper.html"
    show(plot, file_path=str(second_file))
    assert second_file.exists()


def test_default_exp_series_prefix_matching():
    df = pd.DataFrame(
        {
            "Region": ["India (PPP)", "World"],
            2000: [100, 200],
            2001: [110, 220],
        }
    )

    chart = LineGraph({"economics": df})
    chart.default_df("economics")
    chart.default_exp(series("India"))

    key, series_names, expressions = chart._determine_defaults()
    assert key == "economics"
    assert series_names == ["India (PPP)"]
    # expression should map to placeholder using the reference name
    assert expressions == ["1"]


def test_default_df_prefix_matching():
    df = pd.DataFrame(
        {
            "Region": ["Alpha", "Beta"],
            2000: [10, 20],
            2001: [15, 25],
        }
    )

    chart = LineGraph({"gdp-per-capita-worldbank-constant-usd": df})
    chart.default_df("gdp-per-capita-worldbank")

    key, series_names, expressions = chart._determine_defaults()
    assert key == "gdp-per-capita-worldbank-constant-usd"
    assert series_names == ["Alpha"]
    assert expressions == ["1"]


def test_custom_title_overrides_mapping(tmp_path):
    df = pd.DataFrame(
        {
            "Region": ["Alpha", "Beta"],
            2000: [10, 20],
            2001: [15, 25],
        }
    )
    chart = LineGraph({"economics": df})
    chart.default_df("economics")
    chart.title("Custom GDP Chart")
    output = tmp_path / "custom_title.html"
    chart.show(str(output))
    html = output.read_text(encoding="utf-8")
    assert "<title>Custom GDP Chart</title>" in html
    assert '<h1 id="chart-title">Custom GDP Chart</h1>' in html


def test_default_scale_validation():
    df = pd.DataFrame(
        {
            "Region": ["Alpha"],
            "2000": [10],
        }
    )
    chart = LineGraph({"dataset": df})
    chart.default_df("dataset")
    chart.default_exp(series("Alpha"))

    chart.default_scale("linear")
    chart.default_scale("log")

    try:
        chart.default_scale("invalid")
        assert False, "Expected ValueError for invalid scale"
    except ValueError:
        pass
