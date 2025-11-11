import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # type: ignore  # noqa: E402

from karana import LineGraph, series  # noqa: E402


def test_line_graph_generates_html():
    df = pd.DataFrame(
        {
            "Region": ["India", "World", "China"],
            2018: [90, 180, 120],
            2019: [100, 200, 140],
            2020: [110, 220, 160],
        }
    )

    chart = LineGraph({"gdp_ppp": df})
    chart.default_df("gdp_ppp")
    chart.default_exp(series("India") / series("World"))

    output_file = PROJECT_ROOT / "test_line_graph_output.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    chart.show(str(output_file))

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "karana LineGraph" in content
    assert "payload =" in content

