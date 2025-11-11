import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # type: ignore  # noqa: E402

from karana import LineGraph, series  # noqa: E402


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

    output_file = PROJECT_ROOT / "test_line_graph_output.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    chart.show(str(output_file))

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "karana LineGraph" in content
    assert "payload =" in content
    assert "+ Add Expression" in content
    assert "Remove series" in content or "Remove expression" in content
    assert "Sample Admin" in content
    assert "Administrations" in content
    assert "admin-legend-item" in content
    assert "xAxisConfig.range = [xRangeMin, xRangeMax];" in content


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

