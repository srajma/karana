from __future__ import annotations

import html
from pathlib import Path
from typing import List, Optional, Union

from ._line_graph import LineGraph
from ._scatter_plot import ScatterPlot


class Plot:
    """
    Container for combining multiple LineGraph instances into a single HTML page.
    """

    def __init__(self, title: Optional[str] = None) -> None:
        self._title = title or "karana Plot"
        self._entries: List[tuple[str, object]] = []

    def add(self, graph: Union[LineGraph, ScatterPlot], *, title: Optional[str] = None) -> "Plot":
        if not isinstance(graph, (LineGraph, ScatterPlot)):
            raise TypeError("Plot.add expects a LineGraph or ScatterPlot instance.")
        # title parameter remains for backward compatibility but is ignored.
        self._entries.append(("graph", graph))
        return self

    def html(self, markup: str) -> "Plot":
        if not isinstance(markup, str):
            raise TypeError("Plot.html expects a string of HTML markup.")
        self._entries.append(("html", markup))
        return self

    def show(self, file_path: str, type: str = "html") -> Path:
        return show(self, file_path=file_path, type=type)

    def _render_html(self) -> str:
        if not self._entries:
            raise ValueError("Plot has no graphs to render. Call add() first.")

        blocks = []
        for kind, payload in self._entries:
            if kind == "graph":
                graph_html = payload._render_html()  # type: ignore[attr-defined]
                iframe_doc = html.escape(graph_html, quote=True)
                blocks.append(
                    f"""
    <iframe
      class="plot-frame"
      srcdoc="{iframe_doc}"
      loading="lazy"
      sandbox="allow-scripts allow-same-origin"
    ></iframe>
    """
                )
            elif kind == "html":
                blocks.append(f'\n    <div class="plot-html">{payload}</div>\n')
            else:
                raise ValueError("Unknown plot entry type encountered.")

        frames_html = "\n".join(blocks)
        title_text = html.escape(self._title)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title_text}</title>
  <style>
    :root {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      color: #1f2933;
      background: #f9fafb;
    }}
    body {{
      margin: 0;
      padding: 1.5rem;
      background: #ffffff;
    }}
    h1 {{
      font-size: 1.5rem;
      margin: 0 0 1.5rem;
      text-align: center;
    }}
    .plot-container {{
      display: flex;
      flex-direction: column;
      /*gap: 2rem;*/
      max-width: 1100px;
      margin: 0 auto 2rem;
    }}
    .plot-frame {{
      width: 100%;
      border: none;
      min-height: 540px;
      background: transparent;
      display: block;
    }}
    .plot-html {{
      width: 100%;
      color: #1f2933;
      font-size: 1rem;
      line-height: 1.6;
    }}
  </style>
</head>
<body>
  <h1>{title_text}</h1>
  <div class="plot-container">
    {frames_html}
  </div>
</body>
</html>
"""


def show(item, *, file_path: str, type: str = "html") -> Path:
    """
    Generic helper to render either a LineGraph or a Plot into an HTML file.
    """
    if type.lower() != "html":
        raise ValueError("Only HTML rendering is currently supported.")

    if isinstance(item, LineGraph):
        html_output = item._render_html()
    elif isinstance(item, ScatterPlot):
        html_output = item._render_html()
    elif isinstance(item, Plot):
        html_output = item._render_html()
    else:
        raise TypeError("karana.show() expects a LineGraph or Plot instance.")

    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_output, encoding="utf-8")
    return output_path


