from __future__ import annotations

import html
from pathlib import Path
from typing import List, Optional

from ._line_graph import LineGraph


class Plot:
    """
    Container for combining multiple LineGraph instances into a single HTML page.
    """

    def __init__(self, title: Optional[str] = None) -> None:
        self._title = title or "karana Plot"
        self._entries: List[tuple[LineGraph, Optional[str]]] = []

    def add(self, graph: LineGraph, *, title: Optional[str] = None) -> "Plot":
        if not isinstance(graph, LineGraph):
            raise TypeError("Plot.add expects a LineGraph instance.")
        self._entries.append((graph, title))
        return self

    def show(self, file_path: str, type: str = "html") -> Path:
        return show(self, file_path=file_path, type=type)

    def _render_html(self) -> str:
        if not self._entries:
            raise ValueError("Plot has no graphs to render. Call add() first.")

        cards = []
        for index, (graph, title) in enumerate(self._entries, start=1):
            graph_html = graph._render_html()
            iframe_doc = html.escape(graph_html, quote=True)
            header = title or f"Chart {index}"
            cards.append(
                f"""
        <section class="plot-card">
          <header>{html.escape(header)}</header>
          <iframe
            class="plot-frame"
            srcdoc="{iframe_doc}"
            loading="lazy"
            sandbox="allow-scripts allow-same-origin"
          ></iframe>
        </section>
        """
            )

        cards_html = "\n".join(cards)
        title_text = html.escape(self._title)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title_text}</title>
  <style>
    :root {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #1f2933;
      background: #f9fafb;
    }}
    body {{
      margin: 0;
      padding: 1.5rem;
    }}
    h1 {{
      font-size: 1.5rem;
      margin: 0 0 1.5rem;
      text-align: center;
    }}
    .plot-container {{
      display: grid;
      gap: 1.5rem;
      max-width: 1100px;
      margin: 0 auto 2rem;
    }}
    .plot-card {{
      background: #ffffff;
      border-radius: 14px;
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
      padding: 1rem 1rem 1.25rem;
      border: 1px solid #e2e8f0;
    }}
    .plot-card > header {{
      font-size: 1rem;
      font-weight: 600;
      color: #1f2937;
      margin-bottom: 0.75rem;
    }}
    .plot-frame {{
      width: 100%;
      border: none;
      border-radius: 8px;
      min-height: 520px;
      background: #ffffff;
    }}
  </style>
</head>
<body>
  <h1>{title_text}</h1>
  <div class="plot-container">
    {cards_html}
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
    elif isinstance(item, Plot):
        html_output = item._render_html()
    else:
        raise TypeError("karana.show() expects a LineGraph or Plot instance.")

    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_output, encoding="utf-8")
    return output_path


