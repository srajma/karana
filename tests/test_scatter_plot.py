from __future__ import annotations

import sys
from pathlib import Path

import numpy as np  # noqa: E402
import pandas as pd  # type: ignore  # noqa: E402
import pytest  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from karana import Plot, ScatterPlot, show  # noqa: E402
from karana.loaders.owid import load_chart  # noqa: E402

TEST_OUTPUTS_PATH = PROJECT_ROOT / "test_outputs"


def _build_sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Region": ["Alpha", "Beta", "Gamma"],
            "2010": [1.0, 2.0, None],
            "2011": [1.5, 2.5, 3.5],
            "2012": [2.0, 3.0, 4.0],
        }
    )


def test_scatter_plot_renders_html(tmp_path) -> None:
    df = _build_sample_df()
    scatter = ScatterPlot({"sample": df}).default_year(2011)
    output_file = tmp_path / "scatter.html"
    scatter.show(str(output_file))

    html = output_file.read_text(encoding="utf-8")
    assert "payload =" in html
    assert '"sample"' in html
    assert '"2011"' in html
    assert "Plotly.react" in html
    assert "x-axis-select" in html
    assert "y-axis-select" in html
    assert "year-slider" in html
    assert "+ Add Series" not in html


def test_scatter_plot_payload_defaults() -> None:
    df = _build_sample_df()
    scatter = ScatterPlot({"demo": df})
    html = scatter._render_html()
    assert '"x": "demo"' in html
    assert '"y": "demo"' in html
    assert '"year": "2012"' in html  # last year should be default


def test_scatter_plot_generates_html(tmp_path):
    df_x = pd.DataFrame(
        {
            "Region": ["India", "China", "World"],
            2018: [90, 82, 70],
            2019: [95, 85, 74],
            2020: [100, 90, 78],
        }
    )

    df_y = pd.DataFrame(
        {
            "Region": ["India", "China", "World"],
            2018: [5.0, 8.0, 6.5],
            2019: [5.5, 8.5, 6.7],
            2020: [6.0, np.nan, 6.9],
        }
    )

    chart = ScatterPlot({"gdp": df_x, "life": df_y})
    chart.default_axes(x="gdp", y="life")
    chart.default_year(2019)

    output_file = tmp_path / "scatter.html"
    chart.show(str(output_file))

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert 'id="year-slider"' in content
    assert "+ Add Series" not in content
    assert "payload =" in content


def test_plot_handles_scatter(tmp_path):
    df = pd.DataFrame(
        {
            "Region": ["Alpha", "Beta"],
            2000: [10, 20],
            2001: [12, 22],
            2002: [14, 24],
        }
    )

    scatter = ScatterPlot({"dataset_one": df, "dataset_two": df})
    scatter.default_axes(x="dataset_one", y="dataset_two")

    plot = Plot("Scatter Only Plot")
    plot.add(scatter)

    output_file = tmp_path / "scatter_plot.html"
    show(plot, file_path=str(output_file))

    assert output_file.exists()
    html = output_file.read_text(encoding="utf-8")
    assert html.count("<iframe") == 1
    assert "+ Add Series" not in html


@pytest.mark.integration
def test_scatter_plot_with_owid_datasets(tmp_path):
    try:
        life_expectancy = load_chart("life-expectancy")
        gdp_per_capita = load_chart("gdp-per-capita-maddison-project-database")
    except Exception as exc:  # pragma: no cover - network variability
        pytest.skip(f"OWID chart fetch failed: {exc}")

    life_key, life_df = next(iter(life_expectancy.items()))
    gdp_key, gdp_df = next(iter(gdp_per_capita.items()))

    scatter = ScatterPlot({life_key: life_df, gdp_key: gdp_df})
    scatter.default_axes(x=gdp_key, y=life_key)
    scatter.default_year(2019)
    scatter.titles(
        {
            "life-expectancy": "Life Expectancy",
            "gdp-per-capita-maddison-project-database": "GDP per Capita (Maddison Project)",
        }
    )

    # ensure directory exists
    TEST_OUTPUTS_PATH.mkdir(parents=True, exist_ok=True)
    output_path = TEST_OUTPUTS_PATH / "owid_scatter_life_vs_gdp.html"
    scatter.show(str(output_path))

    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "payload =" in html
    assert gdp_key in html
    assert life_key in html
    assert "+ Add Series" not in html
