from __future__ import annotations

import html as html_utils
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import pandas as pd  # type: ignore

from ._line_graph import _normalize_year


@dataclass(frozen=True)
class _Dataset:
    years: List[str]
    regions: Dict[str, List[Optional[float]]]


class ScatterPlot:
    """
    Construct interactive HTML-based scatter plots from pandas dataframes.

    Each dataframe is expected to include a `Region` column followed by one column per year.
    Users select which dataset populates the X axis and which populates the Y axis, then
    choose regions (series) and a year to plot. Each region is rendered as one point on the
    scatter chart for the selected year.
    """

    def __init__(self, dfs: Mapping[str, pd.DataFrame]) -> None:
        if not dfs:
            raise ValueError("ScatterPlot requires at least one dataframe.")

        self._datasets: Dict[str, _Dataset] = {}
        for key, df in dfs.items():
            if not isinstance(df, pd.DataFrame):
                raise TypeError(f"Dataframe for key '{key}' must be a pandas DataFrame.")
            self._datasets[str(key)] = self._convert_df(df, str(key))

        self._default_x: Optional[str] = None
        self._default_y: Optional[str] = None
        self._default_regions: Optional[List[str]] = None
        self._default_year: Optional[str] = None
        self._dataset_titles: Dict[str, str] = {}

    # --------------------------------------------------------------------- configuration

    def default_axes(self, *, x: str, y: str) -> "ScatterPlot":
        self._default_x = self._resolve_dataset_key(x)
        self._default_y = self._resolve_dataset_key(y)
        return self

    def default_regions(self, *regions: str | Sequence[str]) -> "ScatterPlot":
        if not regions:
            raise ValueError("default_regions requires at least one region.")

        if len(regions) == 1 and isinstance(regions[0], Sequence) and not isinstance(
            regions[0], (str, bytes)
        ):
            flattened: Iterable[Any] = regions[0]  # type: ignore[assignment]
        else:
            flattened = regions

        normalised: List[str] = []
        for entry in flattened:
            text = str(entry).strip()
            if not text:
                raise ValueError("Region names must not be empty.")
            normalised.append(text)

        if not normalised:
            raise ValueError("default_regions requires at least one region.")

        self._default_regions = normalised
        return self

    def default_year(self, year: Any) -> "ScatterPlot":
        self._default_year = _normalize_year(year)
        return self

    def titles(self, mapping: Mapping[str, str]) -> "ScatterPlot":
        if not isinstance(mapping, Mapping):
            raise TypeError("titles expects a mapping from dataset keys to display titles.")
        self._dataset_titles = {str(k): str(v) for k, v in mapping.items()}
        return self

    # ------------------------------------------------------------------------------------

    def show(self, file_path: str, type: str = "html") -> Path:
        if type.lower() != "html":
            raise ValueError("Only HTML rendering is currently supported.")

        html_output = self._render_html()

        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_output, encoding="utf-8")
        return output_path

    # ------------------------------------------------------------------------------------

    def _render_html(self) -> str:
        x_key, y_key, default_year, default_regions = self._determine_defaults()
        title_text = html_utils.escape(
            f"{self._resolve_dataset_title(y_key)} vs {self._resolve_dataset_title(x_key)}"
        )

        payload = {
            "datasets": {
                key: {
                    "years": dataset.years,
                    "regions": dataset.regions,
                }
                for key, dataset in self._datasets.items()
            },
            "defaults": {
                "axes": {"x": x_key, "y": y_key},
                "year": default_year,
                "regions": default_regions,
            },
            "titles": {
                "mapping": self._dataset_titles,
            },
        }

        payload_json = json.dumps(payload, ensure_ascii=False)

        html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title_text}</title>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
  <style>
    :root {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      color: #1f2933;
      background: #f9fafb;
    }}
    body {{
      margin: 0;
      background: #ffffff;
    }}
    .karana-container {{
      max-width: 960px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      padding: 1.5rem 1.75rem 2rem;
    }}
    h1 {{
      font-size: 1.5rem;
      margin: 0 0 1.5rem;
      font-weight: 300;
    }}
    .controls {{
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      margin-bottom: 1.5rem;
    }}
    .control-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
    }}
    label {{
      font-weight: 500;
      font-size: 0.95rem;
      min-width: 120px;
    }}
    select {{
      padding: 0.5rem 0.75rem;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
      font-size: 0.95rem;
      min-width: 220px;
      background: #f8fafc;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    select:focus {{
      outline: none;
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
      background: white;
    }}
    #year-slider {{
      flex: 1;
      min-width: 240px;
      accent-color: #2563eb;
    }}
    .year-value {{
      font-weight: 600;
      font-size: 1rem;
      min-width: 3rem;
      text-align: center;
      color: #1f2937;
    }}
    .region-list {{
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      width: 100%;
    }}
    .region-slot {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .region-slot span {{
      font-weight: 500;
      color: #475569;
      min-width: 1.5rem;
      text-align: right;
    }}
    button {{
      border: none;
      background: #2563eb;
      color: white;
      border-radius: 999px;
      padding: 0.45rem 0.9rem;
      font-size: 0.9rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s ease, box-shadow 0.2s ease;
    }}
    button:hover {{
      background: #1d4ed8;
      box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
    }}
    .remove-region {{
      background: #e11d48;
      padding: 0.35rem 0.7rem;
      border-radius: 999px;
      font-size: 0.85rem;
    }}
    .remove-region:hover {{
      background: #be123c;
    }}
    .status-message {{
      min-height: 1.25rem;
      font-size: 0.9rem;
      color: #dc2626;
    }}
    #chart {{
      min-height: 500px;
    }}
  </style>
</head>
<body>
  <div class="karana-container">
    <div class="controls">
      <div class="control-group">
        <label for="x-axis-select">X Axis</label>
        <select id="x-axis-select"></select>
      </div>
      <div class="control-group">
        <label for="y-axis-select">Y Axis</label>
        <select id="y-axis-select"></select>
      </div>
      <div class="control-group">
        <label for="year-slider">Year</label>
        <input id="year-slider" type="range" min="0" max="0" step="1" value="0" />
        <span id="year-value" class="year-value"></span>
      </div>
      <div class="control-group">
        <label>Series</label>
        <div id="region-selects" class="region-list"></div>
        <button id="add-region" type="button">+ Add Series</button>
      </div>
      <div class="status-message" id="status-message"></div>
    </div>
    <h1 id="chart-title">{title_text}</h1>
    <div id="chart"></div>
  </div>

  <script>
    const payload = {payload_json};

    const state = {{
      xKey: payload.defaults.axes.x,
      yKey: payload.defaults.axes.y,
      year: payload.defaults.year,
      yearIndex: null,
      yearOptions: [],
      regionNames: [...payload.defaults.regions],
    }};

    const xAxisSelect = document.getElementById("x-axis-select");
    const yAxisSelect = document.getElementById("y-axis-select");
    const yearSlider = document.getElementById("year-slider");
    const yearValue = document.getElementById("year-value");
    const regionContainer = document.getElementById("region-selects");
    const addRegionButton = document.getElementById("add-region");
    const statusMessage = document.getElementById("status-message");
    const chartTitle = document.getElementById("chart-title");

    function getDataset(key) {{
      return payload.datasets[key];
    }}

    function resolveDatasetTitle(key) {{
      const mapping = (payload.titles && payload.titles.mapping) || null;
      if (mapping) {{
        if (Object.prototype.hasOwnProperty.call(mapping, key)) {{
          return mapping[key];
        }}
        let bestPrefix = null;
        let bestLength = -1;
        Object.keys(mapping).forEach((prefix) => {{
          if (key.startsWith(prefix) && prefix.length > bestLength) {{
            bestPrefix = prefix;
            bestLength = prefix.length;
          }}
        }});
        if (bestPrefix !== null) {{
          return mapping[bestPrefix];
        }}
      }}
      return key;
    }}

    function computeCommonYears(xKey, yKey) {{
      const xYears = getDataset(xKey).years;
      const yYears = getDataset(yKey).years;
      const ySet = new Set(yYears);
      return xYears.filter((year) => ySet.has(year));
    }}

    function computeCommonRegions(xKey, yKey) {{
      const xRegions = Object.keys(getDataset(xKey).regions);
      const yRegions = new Set(Object.keys(getDataset(yKey).regions));
      return xRegions.filter((region) => yRegions.has(region));
    }}

    function updateChartTitle() {{
      chartTitle.textContent = resolveDatasetTitle(state.yKey) + " vs " + resolveDatasetTitle(state.xKey);
    }}

    function buildAxisSelect(select, selectedKey) {{
      const options = Object.keys(payload.datasets)
        .map((key) => {{
          const selected = key === selectedKey ? "selected" : "";
          return `<option value="${{key}}" ${{selected}}>${{key}}</option>`;
        }})
        .join("");
      select.innerHTML = options;
      select.value = selectedKey;
    }}

    function ensureYearStateAvailable() {{
      const years = computeCommonYears(state.xKey, state.yKey);
      if (!years || years.length === 0) {{
        throw new Error("Selected axes do not share any year columns.");
      }}
      let index = state.yearIndex;
      if (index === null || index < 0 || index >= years.length) {{
        index = years.indexOf(state.year);
      }}
      if (index === -1) {{
        index = years.length - 1;
      }}
      if (index < 0) {{
        index = 0;
      }}
      state.yearIndex = index;
      state.year = years[index];
      state.yearOptions = years;
      yearSlider.min = 0;
      yearSlider.max = years.length - 1;
      yearSlider.step = 1;
      yearSlider.value = index;
      yearSlider.disabled = years.length <= 1;
      yearValue.textContent = state.year;
    }}

    function ensureRegionSelectionsAvailable() {{
      const available = computeCommonRegions(state.xKey, state.yKey);
      if (!available || available.length === 0) {{
        throw new Error("Selected axes do not share any regions.");
      }}
      if (!Array.isArray(state.regionNames) || state.regionNames.length === 0) {{
        state.regionNames = [available[0]];
        return;
      }}
      state.regionNames = state.regionNames.map((name, index) => {{
        if (available.includes(name)) {{
          return name;
        }}
        return available[Math.min(index, available.length - 1)];
      }});
      if (state.regionNames.length === 0) {{
        state.regionNames = [available[0]];
      }}
    }}

    function buildRegionControls() {{
      regionContainer.innerHTML = "";
      const available = computeCommonRegions(state.xKey, state.yKey);

      state.regionNames.forEach((regionName, idx) => {{
        const slot = document.createElement("div");
        slot.className = "region-slot";

        const label = document.createElement("span");
        label.textContent = idx + 1;
        slot.appendChild(label);

        const select = document.createElement("select");
        available.forEach((name) => {{
          const option = document.createElement("option");
          option.value = name;
          option.textContent = name;
          if (name === regionName) {{
            option.selected = true;
          }}
          select.appendChild(option);
        }});

        select.addEventListener("change", () => {{
          state.regionNames[idx] = select.value;
          updateChart();
        }});

        slot.appendChild(select);

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "remove-region";
        remove.textContent = "Remove";
        remove.title = "Remove series";
        remove.addEventListener("click", () => {{
          if (state.regionNames.length <= 1) {{
            statusMessage.textContent = "At least one series is required.";
            return;
          }}
          removeRegionAt(idx);
        }});
        slot.appendChild(remove);

        regionContainer.appendChild(slot);
      }});
    }}

    function addRegionSlot() {{
      const available = computeCommonRegions(state.xKey, state.yKey);
      if (!available || available.length === 0) {{
        statusMessage.textContent = "Cannot add series: no overlapping regions.";
        return;
      }}
      const unused = available.find((name) => !state.regionNames.includes(name));
      state.regionNames.push(unused || available[0]);
      buildRegionControls();
      updateChart();
    }}

    function removeRegionAt(index) {{
      state.regionNames.splice(index, 1);
      buildRegionControls();
      updateChart();
    }}

    function updateChart() {{
      try {{
        statusMessage.textContent = "";
        ensureYearStateAvailable();
        ensureRegionSelectionsAvailable();
        buildRegionControls();

        const datasetX = getDataset(state.xKey);
        const datasetY = getDataset(state.yKey);
        const yearIdx = state.yearIndex;
        const yearLabel = state.yearOptions[yearIdx];

        const traces = [];
        const numericValuesX = [];
        const numericValuesY = [];

        state.regionNames.forEach((regionName) => {{
          const seriesX = datasetX.regions[regionName];
          const seriesY = datasetY.regions[regionName];
          if (!seriesX || !seriesY) {{
            return;
          }}
          const xValue = seriesX[yearIdx];
          const yValue = seriesY[yearIdx];
          if (xValue == null || yValue == null || !Number.isFinite(xValue) || !Number.isFinite(yValue)) {{
            return;
          }}
          numericValuesX.push(xValue);
          numericValuesY.push(yValue);
          traces.push({{
            type: "scatter",
            mode: "markers",
            name: regionName,
            x: [xValue],
            y: [yValue],
            marker: {{
              size: 12,
              opacity: 0.85,
              line: {{ width: 0 }},
            }},
            hovertemplate:
              "Region: " + regionName + "<br>X: %{{x}}<br>Y: %{{y}}<extra></extra>",
          }});
        }});

        if (traces.length === 0) {{
          Plotly.purge("chart");
          statusMessage.textContent = "No numeric values available for the selected year.";
          return;
        }}

        const xMin = Math.min(...numericValuesX);
        const xMax = Math.max(...numericValuesX);
        const yMin = Math.min(...numericValuesY);
        const yMax = Math.max(...numericValuesY);

        function expandRange(minValue, maxValue) {{
          let lower = minValue;
          let upper = maxValue;
          if (lower === upper) {{
            const padding = Math.max(1, Math.abs(lower) * 0.1);
            lower -= padding;
            upper += padding;
          }} else {{
            const span = upper - lower;
            const padding = span * 0.08;
            lower -= padding;
            upper += padding;
          }}
          return [lower, upper];
        }}

        const [xLower, xUpper] = expandRange(xMin, xMax);
        const [yLower, yUpper] = expandRange(yMin, yMax);

        Plotly.react("chart", traces, {{
          margin: {{ l: 80, r: 30, t: 20, b: 60 }},
          xaxis: {{
            title: resolveDatasetTitle(state.xKey),
            range: [xLower, xUpper],
            showgrid: true,
            gridcolor: "#e2e8f0",
            gridwidth: 1,
            zeroline: false,
          }},
          yaxis: {{
            title: resolveDatasetTitle(state.yKey),
            range: [yLower, yUpper],
            showgrid: true,
            gridcolor: "#e2e8f0",
            gridwidth: 1,
            zeroline: false,
          }},
          showlegend: true,
          legend: {{ orientation: "h", y: -0.2 }},
        }});

        yearValue.textContent = yearLabel;
        adjustParentFrame();
      }} catch (error) {{
        statusMessage.textContent = error.message || String(error);
        Plotly.purge("chart");
      }}
    }}

    xAxisSelect.addEventListener("change", () => {{
      state.xKey = xAxisSelect.value;
      ensureYearStateAvailable();
      ensureRegionSelectionsAvailable();
      buildRegionControls();
      updateChartTitle();
      updateChart();
    }});

    yAxisSelect.addEventListener("change", () => {{
      state.yKey = yAxisSelect.value;
      ensureYearStateAvailable();
      ensureRegionSelectionsAvailable();
      buildRegionControls();
      updateChartTitle();
      updateChart();
    }});

    yearSlider.addEventListener("input", () => {{
      const value = Number(yearSlider.value);
      if (!Array.isArray(state.yearOptions)) {{
        return;
      }}
      if (value >= 0 && value < state.yearOptions.length) {{
        state.yearIndex = value;
        state.year = state.yearOptions[value];
        yearValue.textContent = state.year;
        updateChart();
      }}
    }});

    addRegionButton.addEventListener("click", () => {{
      addRegionSlot();
    }});

    function init() {{
      buildAxisSelect(xAxisSelect, state.xKey);
      buildAxisSelect(yAxisSelect, state.yKey);
      ensureYearStateAvailable();
      ensureRegionSelectionsAvailable();
      buildRegionControls();
      updateChartTitle();
      updateChart();
    }}

    init();

    function adjustParentFrame() {{
      if (!window.frameElement) {{
        return;
      }}
      const update = () => {{
        window.frameElement.style.height = document.body.scrollHeight + "px";
      }};
      update();
      if (typeof ResizeObserver === "function") {{
        const observer = new ResizeObserver(update);
        observer.observe(document.body);
      }} else {{
        window.addEventListener("load", update);
      }}
    }}
  </script>
</body>
</html>
"""
        return html_output

    def _determine_defaults(self) -> tuple[str, str, str, List[str]]:
        if not self._datasets:
            raise ValueError("ScatterPlot has no datasets to render.")

        x_key = self._resolve_dataset_key(self._default_x or next(iter(self._datasets)))
        if self._default_y is None:
            y_key = next((key for key in self._datasets if key != x_key), x_key)
        else:
            y_key = self._resolve_dataset_key(self._default_y)

        dataset_x = self._datasets[x_key]
        dataset_y = self._datasets[y_key]

        common_years = [year for year in dataset_x.years if year in set(dataset_y.years)]
        if not common_years:
            raise ValueError(
                f"Datasets '{x_key}' and '{y_key}' do not share any year columns."
            )

        if self._default_year and self._default_year in common_years:
            selected_year = self._default_year
        else:
            selected_year = common_years[-1]

        available_regions = self._compute_common_regions(dataset_x, dataset_y)
        if not available_regions:
            raise ValueError(
                f"Datasets '{x_key}' and '{y_key}' do not share any region names."
            )

        if self._default_regions:
            resolved_regions = self._resolve_region_names(available_regions, self._default_regions)
            if not resolved_regions:
                raise ValueError(
                    "default_regions must include at least one region present in both datasets."
                )
        else:
            resolved_regions = available_regions[: min(3, len(available_regions))]

        return x_key, y_key, selected_year, resolved_regions

    def _compute_common_regions(self, dataset_x: _Dataset, dataset_y: _Dataset) -> List[str]:
        y_regions = set(dataset_y.regions.keys())
        return [name for name in dataset_x.regions.keys() if name in y_regions]

    def _resolve_region_names(
        self, available: Sequence[str], references: Sequence[str]
    ) -> List[str]:
        resolved: List[str] = []
        seen: set[str] = set()
        for reference in references:
            match = self._match_region_name(available, reference)
            if match is not None and match not in seen:
                resolved.append(match)
                seen.add(match)
        return resolved

    def _match_region_name(self, available: Sequence[str], reference: str) -> Optional[str]:
        if reference in available:
            return reference
        candidates = [name for name in available if name.startswith(reference)]
        if candidates:
            candidates.sort(key=len)
            return candidates[0]
        lowered_ref = reference.lower()
        ci_candidates = [name for name in available if name.lower().startswith(lowered_ref)]
        if ci_candidates:
            ci_candidates.sort(key=len)
            return ci_candidates[0]
        return None

    def _resolve_dataset_key(self, key: str) -> str:
        if key in self._datasets:
            return key
        best_match: Optional[str] = None
        best_length = -1
        for candidate in self._datasets:
            if candidate.startswith(key):
                if len(candidate) > best_length:
                    best_match = candidate
                    best_length = len(candidate)
        if best_match is not None:
            return best_match
        raise KeyError(f"Unknown dataframe key '{key}'.")

    def _resolve_dataset_title(self, key: str) -> str:
        if key in self._dataset_titles:
            return self._dataset_titles[key]
        best_match: Optional[str] = None
        best_title: Optional[str] = None
        for prefix, title in self._dataset_titles.items():
            if key.startswith(prefix):
                if best_match is None or len(prefix) > len(best_match):
                    best_match = prefix
                    best_title = title
        if best_title is not None:
            return best_title
        return key

    def _convert_df(self, df: pd.DataFrame, key: str) -> _Dataset:
        if "Region" not in df.columns:
            raise ValueError(f"Dataframe '{key}' must include a 'Region' column.")

        year_columns = [col for col in df.columns if col != "Region"]
        if not year_columns:
            raise ValueError(f"Dataframe '{key}' must include at least one year column.")

        years = [str(col) for col in year_columns]

        regions: Dict[str, List[Optional[float]]] = {}
        for _, row in df.iterrows():
            region_name = str(row["Region"])
            values: List[Optional[float]] = []
            for col in year_columns:
                value = row[col]
                if pd.isna(value):
                    values.append(None)
                else:
                    try:
                        values.append(float(value))
                    except (TypeError, ValueError):
                        raise ValueError(
                            f"Non-numeric value encountered in dataframe '{key}' for region '{region_name}', column '{col}'."
                        ) from None
            regions[region_name] = values

        if not regions:
            raise ValueError(f"Dataframe '{key}' must include at least one region row.")

        return _Dataset(years=years, regions=regions)



