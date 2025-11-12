from __future__ import annotations

import html as html_utils
import json
from collections.abc import Sequence as _Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import pandas as pd  # type: ignore


def _normalize_year(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(int(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("Year values must not be empty strings.")
        if text.isdigit():
            return text
        try:
            numeric = float(text)
        except ValueError as exc:
            raise ValueError(f"Invalid year value '{value}'.") from exc
        return str(int(numeric))
    raise TypeError(f"Year value of type {type(value)!r} is not supported.")


@dataclass(frozen=True)
class _Dataset:
    years: List[str]
    regions: Dict[str, List[Optional[float]]]


class ScatterPlot:
    """
    Construct interactive HTML-based scatter plots from multiple pandas dataframes.
    """

    def __init__(self, dfs: Mapping[str, pd.DataFrame]) -> None:
        if not dfs:
            raise ValueError("ScatterPlot requires at least one dataframe.")

        self._datasets: Dict[str, _Dataset] = {}
        for key, df in dfs.items():
            if not isinstance(df, pd.DataFrame):
                raise TypeError(f"Dataframe for key '{key}' must be a pandas DataFrame.")
            self._datasets[key] = self._convert_df(df, key)

        if len(self._datasets) == 1:
            (first_key,) = self._datasets.keys()
            self._default_axes: Dict[str, str] = {"x": first_key, "y": first_key}
        else:
            keys = list(self._datasets.keys())
            self._default_axes = {"x": keys[0], "y": keys[1]}

        self._default_regions: Optional[List[str]] = None
        self._default_year: Optional[str] = None
        self._dataset_titles: Dict[str, str] = {}

    # --------------------------------------------------------------------- configuration

    def default_axes(self, *, x: str, y: str) -> "ScatterPlot":
        """
        Set default datasets for the X and Y axes. Keys can be prefixes of dataset names.
        """
        self._default_axes["x"] = self._resolve_dataset_key(x)
        self._default_axes["y"] = self._resolve_dataset_key(y)
        return self

    def default_regions(self, *regions: str | _Sequence[str]) -> "ScatterPlot":
        """
        Provide default region selections. Accepts either multiple string arguments or
        a single iterable of strings.
        """
        if not regions:
            raise ValueError("default_regions requires at least one region name.")

        if len(regions) == 1 and isinstance(regions[0], _Sequence) and not isinstance(
            regions[0], (str, bytes)
        ):
            region_list = list(regions[0])  # type: ignore[arg-type]
        else:
            region_list = list(regions)

        if not region_list:
            raise ValueError("default_regions requires at least one region name.")

        normalized = [str(region) for region in region_list]
        self._default_regions = normalized
        return self

    def default_year(self, year: Any) -> "ScatterPlot":
        """
        Set the default year to display when rendering the scatter plot.
        """
        self._default_year = _normalize_year(year)
        return self

    def titles(self, mapping: Mapping[str, str]) -> "ScatterPlot":
        """
        Provide display titles for datasets. Accepts exact keys or key prefixes.
        """
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
        (
            x_axis_key,
            y_axis_key,
            default_regions,
            default_year,
            default_years,
        ) = self._determine_defaults()

        payload = {
            "datasets": {
                key: {
                    "years": dataset.years,
                    "regions": dataset.regions,
                }
                for key, dataset in self._datasets.items()
            },
            "defaults": {
                "axes": {"x": x_axis_key, "y": y_axis_key},
                "regions": default_regions,
                "year": default_year,
                "availableYears": default_years,
            },
            "titles": {
                "mapping": self._dataset_titles,
            },
        }

        payload_json = json.dumps(payload, ensure_ascii=False)

        x_axis_title = html_utils.escape(self._resolve_dataset_title(x_axis_key))
        y_axis_title = html_utils.escape(self._resolve_dataset_title(y_axis_key))
        page_title = f"{x_axis_title} vs {y_axis_title}"

        html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{page_title}</title>
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
      max-width: 1180px;
      margin: 0 auto;
      background: #ffffff;
      padding: 1.5rem 1.75rem 2rem;
    }}
    h1 {{
      font-size: 1.5rem;
      margin: 0 0 1rem;
    }}
    .controls {{
      display: flex;
      flex-direction: column;
      gap: 1rem;
      margin-bottom: 1.25rem;
    }}
    .control-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    .control-group {{
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      min-width: 220px;
      flex: 1 1 0;
    }}
    label {{
      font-weight: 500;
      font-size: 0.95rem;
    }}
    select, input[type="range"] {{
      padding: 0.5rem 0.75rem;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
      font-size: 0.95rem;
      background: #f8fafc;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    select:focus, input[type="range"]:focus {{
      outline: none;
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
      background: white;
    }}
    input[type="range"] {{
      height: 36px;
    }}
    .range-meta {{
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      color: #475569;
      margin-top: -0.35rem;
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
      align-self: flex-start;
    }}
    button:hover {{
      background: #1d4ed8;
      box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
    }}
    .region-list {{
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
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
    .region-slot select {{
      flex: 1 1 0;
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
      min-height: 440px;
    }}
  </style>
</head>
<body>
  <div class="karana-container">
    <div class="controls">
      <div class="control-row">
        <div class="control-group">
          <label for="x-axis-select">X axis dataset</label>
          <select id="x-axis-select"></select>
        </div>
        <div class="control-group">
          <label for="y-axis-select">Y axis dataset</label>
          <select id="y-axis-select"></select>
        </div>
      </div>
      <div class="control-row">
        <div class="control-group">
          <label>Series</label>
          <div id="region-selects" class="region-list"></div>
          <button id="add-region" type="button">+ Add Series</button>
        </div>
        <div class="control-group">
          <label for="year-slider">Year: <span id="year-value"></span></label>
          <input id="year-slider" type="range" min="0" max="0" value="0" step="1" />
          <div class="range-meta">
            <span id="year-min"></span>
            <span id="year-max"></span>
          </div>
        </div>
      </div>
      <div class="status-message" id="status-message"></div>
    </div>
    <h1 id="chart-title">{page_title}</h1>
    <div id="chart"></div>
  </div>

  <script>
    const payload = {payload_json};

    const state = {{
      xAxis: payload.defaults.axes.x,
      yAxis: payload.defaults.axes.y,
      regionNames: [...payload.defaults.regions],
      year: payload.defaults.year,
      yearIndex: 0,
    }};

    let availableYears = payload.defaults.availableYears || [];

    const xAxisSelect = document.getElementById("x-axis-select");
    const yAxisSelect = document.getElementById("y-axis-select");
    const regionContainer = document.getElementById("region-selects");
    const addRegionButton = document.getElementById("add-region");
    const yearSlider = document.getElementById("year-slider");
    const yearValue = document.getElementById("year-value");
    const yearMin = document.getElementById("year-min");
    const yearMax = document.getElementById("year-max");
    const statusMessage = document.getElementById("status-message");
    const chartTitle = document.getElementById("chart-title");

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

    function buildDatasetOptions(selectedKey) {{
      return Object.keys(payload.datasets)
        .map((key) => {{
          const title = resolveDatasetTitle(key);
          const selected = key === selectedKey ? "selected" : "";
          return `<option value="${{key}}" ${{selected}}>${{title}}</option>`;
        }})
        .join("");
    }}

    function updateAxisSelects() {{
      xAxisSelect.innerHTML = buildDatasetOptions(state.xAxis);
      yAxisSelect.innerHTML = buildDatasetOptions(state.yAxis);
    }}

    function sortYears(years) {{
      if (years.every((year) => !Number.isNaN(Number(year)))) {{
        return years
          .map((year) => Number(year))
          .sort((a, b) => a - b)
          .map((year) => String(year));
      }}
      return [...years].sort();
    }}

    function computeAvailableYears() {{
      const selectedKeys = [state.xAxis, state.yAxis];
      let intersection = null;
      selectedKeys.forEach((key) => {{
        const dataset = payload.datasets[key];
        if (!dataset) {{
          return;
        }}
        const years = dataset.years;
        if (intersection === null) {{
          intersection = new Set(years);
        }} else {{
          intersection = new Set(
            [...intersection].filter((year) => years.includes(year))
          );
        }}
      }});
      if (!intersection) {{
        return [];
      }}
      return sortYears(Array.from(intersection));
    }}

    function computeAvailableRegions() {{
      const selectedKeys = [state.xAxis, state.yAxis];
      let intersection = null;
      selectedKeys.forEach((key) => {{
        const dataset = payload.datasets[key];
        if (!dataset) {{
          return;
        }}
        const regionNames = Object.keys(dataset.regions);
        if (intersection === null) {{
          intersection = new Set(regionNames);
        }} else {{
          intersection = new Set(
            [...intersection].filter((name) => regionNames.includes(name))
          );
        }}
      }});
      if (!intersection) {{
        return [];
      }}
      return Array.from(intersection).sort();
    }}

    function ensureRegionSelectionsAvailable() {{
      const available = computeAvailableRegions();
      if (available.length === 0) {{
        throw new Error("No overlapping regions across selected datasets.");
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
      const available = computeAvailableRegions();

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
          state.regionNames.splice(idx, 1);
          buildRegionControls();
          updateChart();
        }});
        slot.appendChild(remove);

        regionContainer.appendChild(slot);
      }});
    }}

    function buildYearSlider() {{
      availableYears = computeAvailableYears();
      if (availableYears.length === 0) {{
        statusMessage.textContent = "No overlapping years across selected datasets.";
        yearSlider.disabled = true;
        yearValue.textContent = "N/A";
        yearMin.textContent = "";
        yearMax.textContent = "";
        Plotly.purge("chart");
        return false;
      }}
      yearSlider.disabled = false;
      yearMin.textContent = availableYears[0];
      yearMax.textContent = availableYears[availableYears.length - 1];

      let index = availableYears.indexOf(state.year);
      if (index === -1) {{
        index = availableYears.length - 1;
      }}
      state.yearIndex = index;
      state.year = availableYears[index];
      yearSlider.min = 0;
      yearSlider.max = availableYears.length - 1;
      yearSlider.step = 1;
      yearSlider.value = index;
      yearValue.textContent = state.year;
      return true;
    }}

    function updateChartTitle() {{
      if (!chartTitle) {{
        return;
      }}
      const xTitle = resolveDatasetTitle(state.xAxis);
      const yTitle = resolveDatasetTitle(state.yAxis);
      chartTitle.textContent = `${{xTitle}} vs ${{yTitle}}`;
    }}

    function computeAxisRange(values) {{
      const finite = values.filter((value) => value != null && Number.isFinite(value));
      if (finite.length === 0) {{
        return null;
      }}
      const min = Math.min(...finite);
      const max = Math.max(...finite);
      if (min === max) {{
        const padding = Math.max(1, Math.abs(min) * 0.1);
        return [min - padding, max + padding];
      }}
      const span = max - min;
      const padding = span * 0.08;
      return [min - padding, max + padding];
    }}

    function updateChart() {{
      try {{
        statusMessage.textContent = "";
        const xDataset = payload.datasets[state.xAxis];
        const yDataset = payload.datasets[state.yAxis];
        if (!xDataset || !yDataset) {{
          throw new Error("Selected datasets are not available.");
        }}

        const year = state.year;
        const xYearIdx = xDataset.years.indexOf(year);
        const yYearIdx = yDataset.years.indexOf(year);
        if (xYearIdx === -1 || yYearIdx === -1) {{
          throw new Error("Selected year is unavailable for the chosen datasets.");
        }}

        const traces = [];
        const xValues = [];
        const yValues = [];

        state.regionNames.forEach((regionName) => {{
          const xSeries = xDataset.regions[regionName];
          const ySeries = yDataset.regions[regionName];
          if (!xSeries || !ySeries) {{
            return;
          }}
          const xValue = xSeries[xYearIdx];
          const yValue = ySeries[yYearIdx];
          if (xValue == null || yValue == null) {{
            return;
          }}
          if (!Number.isFinite(xValue) || !Number.isFinite(yValue)) {{
            return;
          }}

          xValues.push(xValue);
          yValues.push(yValue);

          traces.push({{
            type: "scatter",
            mode: "markers",
            name: regionName,
            x: [xValue],
            y: [yValue],
            marker: {{
              size: 12,
              line: {{ width: 1, color: "#ffffff" }},
              opacity: 0.9,
            }},
            hovertemplate: `<b>${{regionName}}</b><br>${{resolveDatasetTitle(state.xAxis)}}: %{{x}}<br>${{resolveDatasetTitle(state.yAxis)}}: %{{y}}<br>Year: ${{
              year
            }}<extra></extra>`,
          }});
        }});

        if (traces.length === 0) {{
          statusMessage.textContent = "No data for the selected year and regions.";
          Plotly.purge("chart");
          return;
        }}

        const xRange = computeAxisRange(xValues);
        const yRange = computeAxisRange(yValues);

        Plotly.react("chart", traces, {{
          margin: {{ l: 60, r: 30, t: 40, b: 60 }},
          hovermode: "closest",
          showlegend: traces.length <= 15,
          xaxis: {{
            title: resolveDatasetTitle(state.xAxis),
            zeroline: false,
            gridcolor: "#e2e8f0",
            gridwidth: 1,
            range: xRange || undefined,
            autorange: xRange ? false : true,
          }},
          yaxis: {{
            title: resolveDatasetTitle(state.yAxis),
            zeroline: false,
            gridcolor: "#e2e8f0",
            gridwidth: 1,
            range: yRange || undefined,
            autorange: yRange ? false : true,
          }},
        }});
        adjustParentFrame();
      }} catch (error) {{
        statusMessage.textContent = error.message;
        Plotly.purge("chart");
      }}
    }}

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

    function init() {{
      updateAxisSelects();
      try {{
        ensureRegionSelectionsAvailable();
        buildRegionControls();
      }} catch (error) {{
        statusMessage.textContent = error.message;
        return;
      }}
      if (!buildYearSlider()) {{
        return;
      }}
      updateChartTitle();
      updateChart();
      adjustParentFrame();
    }}

    xAxisSelect.addEventListener("change", () => {{
      state.xAxis = xAxisSelect.value;
      try {{
        ensureRegionSelectionsAvailable();
      }} catch (error) {{
        statusMessage.textContent = error.message;
        return;
      }}
      buildRegionControls();
      if (!buildYearSlider()) {{
        return;
      }}
      updateChartTitle();
      updateChart();
    }});

    yAxisSelect.addEventListener("change", () => {{
      state.yAxis = yAxisSelect.value;
      try {{
        ensureRegionSelectionsAvailable();
      }} catch (error) {{
        statusMessage.textContent = error.message;
        return;
      }}
      buildRegionControls();
      if (!buildYearSlider()) {{
        return;
      }}
      updateChartTitle();
      updateChart();
    }});

    addRegionButton.addEventListener("click", () => {{
      const available = computeAvailableRegions();
      if (available.length === 0) {{
        statusMessage.textContent = "Cannot add series: no regions available.";
        return;
      }}
      const unused = available.find((name) => !state.regionNames.includes(name));
      state.regionNames.push(unused || available[0]);
      buildRegionControls();
      updateChart();
    }});

    yearSlider.addEventListener("input", () => {{
      const index = Number(yearSlider.value);
      if (Number.isNaN(index) || index < 0 || index >= availableYears.length) {{
        return;
      }}
      state.yearIndex = index;
      state.year = availableYears[index];
      yearValue.textContent = state.year;
      updateChart();
    }});

    init();
  </script>
</body>
</html>
"""
        return html_output

    def _determine_defaults(self) -> tuple[str, str, List[str], str, List[str]]:
        keys = list(self._datasets.keys())
        if not keys:
            raise ValueError("ScatterPlot has no datasets to render.")

        x_key = self._resolve_dataset_key(self._default_axes.get("x", keys[0]))
        y_key = self._resolve_dataset_key(self._default_axes.get("y", keys[-1]))

        x_dataset = self._datasets[x_key]
        y_dataset = self._datasets[y_key]

        common_regions = set(x_dataset.regions.keys()) & set(y_dataset.regions.keys())
        if not common_regions:
            raise ValueError("Selected axis datasets do not share any region names.")

        if self._default_regions is None:
            sorted_regions = sorted(common_regions)
            default_regions = sorted_regions[: min(6, len(sorted_regions))]
            if not default_regions:
                default_regions = [sorted_regions[0]]
        else:
            default_regions = []
            for region in self._default_regions:
                resolved = self._match_region_name(common_regions, region)
                default_regions.append(resolved)
            if not default_regions:
                raise ValueError("default_regions must reference at least one valid region.")

        common_years = set(x_dataset.years) & set(y_dataset.years)
        if not common_years:
            raise ValueError("Selected axis datasets do not share any year columns.")

        sorted_years = self._sort_years(list(common_years))

        if self._default_year is None:
            default_year = sorted_years[-1]
        else:
            normalized = _normalize_year(self._default_year)
            if normalized not in common_years:
                raise ValueError(
                    f"Default year '{normalized}' is not available across selected datasets."
                )
            default_year = normalized

        return x_key, y_key, default_regions, default_year, sorted_years

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

    def _match_region_name(self, available: set[str], reference: str) -> str:
        if reference in available:
            return reference
        candidates = [name for name in available if name.startswith(reference)]
        if candidates:
            candidates.sort(key=len)
            return candidates[0]
        lowered = reference.lower()
        ci_candidates = [name for name in available if name.lower().startswith(lowered)]
        if ci_candidates:
            ci_candidates.sort(key=len)
            return ci_candidates[0]
        raise KeyError(f"Region '{reference}' not found across selected datasets.")

    def _sort_years(self, years: List[str]) -> List[str]:
        def try_numeric(value: str) -> Optional[int]:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        numeric_values = [try_numeric(year) for year in years]
        if all(value is not None for value in numeric_values):
            paired = sorted(zip(numeric_values, years), key=lambda item: item[0])
            return [year for _, year in paired]
        return sorted(years)

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


