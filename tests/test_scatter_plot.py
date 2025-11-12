import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # type: ignore  # noqa: E402

from karana import Plot, ScatterPlot, show  # noqa: E402


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
    chart.default_regions("India", "China")
    chart.default_year(2019)

    output_file = tmp_path / "scatter.html"
    chart.show(str(output_file))

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert 'id="year-slider"' in content
    assert "+ Add Series" in content
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
    scatter.default_regions("Alpha")

    plot = Plot("Scatter Only Plot")
    plot.add(scatter)

    output_file = tmp_path / "scatter_plot.html"
    show(plot, file_path=str(output_file))

    assert output_file.exists()
    html = output_file.read_text(encoding="utf-8")
    assert html.count("<iframe") == 1

