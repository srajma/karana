from __future__ import annotations

import html as html_utils
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

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
    Users select datasets for the X and Y axes and a year to plot. Every region shared between
    the axes is rendered as a single point. Optional dropdowns allow point sizes and colours
    to depend on additional datasets, logarithmic scaling can be toggled, and point paths can
    be traced across time.
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
        self._default_year: Optional[str] = None
        self._dataset_titles: Dict[str, str] = {}
        self._default_size: Optional[str] = None
        self._default_color: Optional[str] = None
        self._default_log_x: bool = False
        self._default_log_y: bool = False
        self._default_size_log: bool = True
        self._default_color_log: bool = True
        self._default_trace_paths: bool = False

    # --------------------------------------------------------------------- configuration

    def default_axes(self, *, x: str, y: str) -> "ScatterPlot":
        self._default_x = self._resolve_dataset_key(x)
        self._default_y = self._resolve_dataset_key(y)
        return self

    def default_year(self, year: Any) -> "ScatterPlot":
        self._default_year = _normalize_year(year)
        return self

    def titles(self, mapping: Mapping[str, str]) -> "ScatterPlot":
        if not isinstance(mapping, Mapping):
            raise TypeError("titles expects a mapping from dataset keys to display titles.")
        self._dataset_titles = {str(k): str(v) for k, v in mapping.items()}
        return self

    def default_size(self, key: Optional[str]) -> "ScatterPlot":
        if key is None:
            self._default_size = None
        else:
            self._default_size = self._resolve_dataset_key(str(key))
        return self

    def default_color(self, key: Optional[str]) -> "ScatterPlot":
        if key is None:
            self._default_color = None
        else:
            self._default_color = self._resolve_dataset_key(str(key))
        return self

    def default_axes_log(self, *, x: Optional[bool] = None, y: Optional[bool] = None) -> "ScatterPlot":
        if x is not None:
            self._default_log_x = bool(x)
        if y is not None:
            self._default_log_y = bool(y)
        return self

    def default_size_log(self, value: bool) -> "ScatterPlot":
        self._default_size_log = bool(value)
        return self

    def default_color_log(self, value: bool) -> "ScatterPlot":
        self._default_color_log = bool(value)
        return self

    def default_trace_paths(self, enabled: bool) -> "ScatterPlot":
        self._default_trace_paths = bool(enabled)
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
        defaults = self._determine_defaults()
        x_key = defaults["x_key"]
        y_key = defaults["y_key"]
        default_year = defaults["year"]
        size_key = defaults["size_key"]
        color_key = defaults["color_key"]

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
                "size": size_key or "auto",
                "color": color_key or "auto",
                "log": {
                    "x": self._default_log_x,
                    "y": self._default_log_y,
                    "size": self._default_size_log,
                    "color": self._default_color_log,
                },
                "tracePaths": self._default_trace_paths,
            },
            "titles": {
                "mapping": self._dataset_titles,
            },
            "seriesOrder": list(self._datasets.keys()),
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
      min-width: 140px;
    }}
    .control-inline {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.75rem;
      min-width: 260px;
    }}
    .control-inline select {{
      flex: 1 1 220px;
    }}
    .checkbox {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.85rem;
      color: #475569;
      user-select: none;
    }}
    .checkbox input[type="checkbox"] {{
      width: 16px;
      height: 16px;
    }}
    .checkbox.is-disabled {{
      opacity: 0.55;
    }}
    select {{
      padding: 0.5rem 0.75rem;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
      font-size: 0.95rem;
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
    button:disabled {{
      background: #94a3b8;
      cursor: not-allowed;
      box-shadow: none;
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
        <div class="control-inline">
          <select id="x-axis-select"></select>
          <label class="checkbox" id="x-axis-log-label">
            <input type="checkbox" id="x-axis-log-toggle" />
            <span>Logarithmic</span>
          </label>
        </div>
      </div>
      <div class="control-group">
        <label for="y-axis-select">Y Axis</label>
        <div class="control-inline">
          <select id="y-axis-select"></select>
          <label class="checkbox" id="y-axis-log-label">
            <input type="checkbox" id="y-axis-log-toggle" />
            <span>Logarithmic</span>
          </label>
        </div>
      </div>
      <div class="control-group">
        <label for="year-slider">Year</label>
        <input id="year-slider" type="range" min="0" max="0" step="1" value="0" />
        <span id="year-value" class="year-value"></span>
      </div>
      <div class="control-group">
        <label for="point-size-select">Point Sizes</label>
        <div class="control-inline">
          <select id="point-size-select"></select>
          <label class="checkbox" id="size-log-label">
            <input type="checkbox" id="size-log-toggle" />
            <span>Logarithmic</span>
          </label>
        </div>
      </div>
      <div class="control-group">
        <label for="point-color-select">Point Colours</label>
        <div class="control-inline">
          <select id="point-color-select"></select>
          <label class="checkbox" id="color-log-label">
            <input type="checkbox" id="color-log-toggle" />
            <span>Logarithmic</span>
          </label>
        </div>
      </div>
      <div class="control-group">
        <label>Point Paths</label>
        <div class="control-inline">
          <label class="checkbox">
            <input type="checkbox" id="trace-paths-toggle" />
            <span>Trace out point paths</span>
          </label>
          <button id="clear-paths" type="button">Clear Point Paths</button>
        </div>
      </div>
      <div class="status-message" id="status-message"></div>
    </div>
    <h1 id="chart-title">{title_text}</h1>
    <div id="chart"></div>
  </div>

  <script>
    const payload = {payload_json};
    const AUTO_VALUE = "auto";

    const state = {{
      xKey: payload.defaults.axes.x,
      yKey: payload.defaults.axes.y,
      year: payload.defaults.year,
      yearIndex: null,
      yearOptions: [],
      sizeKey: payload.defaults.size,
      colorKey: payload.defaults.color,
      logX: Boolean(payload.defaults.log && payload.defaults.log.x),
      logY: Boolean(payload.defaults.log && payload.defaults.log.y),
      sizeLog: payload.defaults.log && payload.defaults.log.size !== undefined ? Boolean(payload.defaults.log.size) : true,
      colorLog: payload.defaults.log && payload.defaults.log.color !== undefined ? Boolean(payload.defaults.log.color) : true,
      tracePaths: Boolean(payload.defaults.tracePaths),
      pathData: {{}},
    }};

    const xAxisSelect = document.getElementById("x-axis-select");
    const yAxisSelect = document.getElementById("y-axis-select");
    const yearSlider = document.getElementById("year-slider");
    const yearValue = document.getElementById("year-value");
    const sizeSelect = document.getElementById("point-size-select");
    const colorSelect = document.getElementById("point-color-select");
    const xAxisLogToggle = document.getElementById("x-axis-log-toggle");
    const yAxisLogToggle = document.getElementById("y-axis-log-toggle");
    const sizeLogToggle = document.getElementById("size-log-toggle");
    const colorLogToggle = document.getElementById("color-log-toggle");
    const xAxisLogLabel = document.getElementById("x-axis-log-label");
    const yAxisLogLabel = document.getElementById("y-axis-log-label");
    const sizeLogLabel = document.getElementById("size-log-label");
    const colorLogLabel = document.getElementById("color-log-label");
    const tracePathsToggle = document.getElementById("trace-paths-toggle");
    const clearPathsButton = document.getElementById("clear-paths");
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

    function updateChartTitle() {{
      chartTitle.textContent = resolveDatasetTitle(state.yKey) + " vs " + resolveDatasetTitle(state.xKey);
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
      return xRegions.filter((region) => yRegions.has(region)).sort();
    }}

    function buildAxisSelect(select, selectedKey) {{
      const options = Object.keys(payload.datasets)
        .map((key) => {{
          const selected = key === selectedKey ? "selected" : "";
          return `<option value="${{key}}" ${{selected}}>${{resolveDatasetTitle(key)}}</option>`;
        }})
        .join("");
      select.innerHTML = options;
      select.value = selectedKey;
    }}

    function buildSeriesSelect(select, selectedKey, {{ includeAuto }}) {{
      const entries = [];
      if (includeAuto) {{
        const selected = selectedKey === AUTO_VALUE ? "selected" : "";
        entries.push(`<option value="${{AUTO_VALUE}}" ${{selected}}>Auto</option>`);
      }}
      payload.seriesOrder.forEach((key) => {{
        const selected = key === selectedKey ? "selected" : "";
        const label = resolveDatasetTitle(key);
        entries.push(`<option value="${{key}}" ${{selected}}>${{label}}</option>`);
      }});
      select.innerHTML = entries.join("");
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

    function ensureDatasetHasYear(datasetKey, yearLabel) {{
      const dataset = getDataset(datasetKey);
      const index = dataset.years.indexOf(yearLabel);
      if (index === -1) {{
        throw new Error("Dataset '" + datasetKey + "' does not contain year " + yearLabel + ".");
      }}
      return index;
    }}

    function updateLogToggleStates() {{
      xAxisLogToggle.checked = state.logX;
      yAxisLogToggle.checked = state.logY;
      sizeLogToggle.checked = state.sizeLog;
      colorLogToggle.checked = state.colorLog;

      const sizeDisabled = state.sizeKey === AUTO_VALUE;
      const colorDisabled = state.colorKey === AUTO_VALUE;
      sizeLogToggle.disabled = sizeDisabled;
      colorLogToggle.disabled = colorDisabled;
      sizeLogLabel.classList.toggle("is-disabled", sizeDisabled);
      colorLogLabel.classList.toggle("is-disabled", colorDisabled);
    }}

    function resetPathData() {{
      state.pathData = {{}};
    }}

    function toNumber(value) {{
      if (value == null) {{
        return null;
      }}
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : null;
    }}

    function updateChart() {{
      try {{
        statusMessage.textContent = "";
        ensureYearStateAvailable();

        const yearLabel = state.year;
        const availableRegions = computeCommonRegions(state.xKey, state.yKey);
        if (!availableRegions || availableRegions.length === 0) {{
          throw new Error("Selected axes do not share any regions.");
        }}

        const xYearIndex = ensureDatasetHasYear(state.xKey, yearLabel);
        const yYearIndex = ensureDatasetHasYear(state.yKey, yearLabel);
        const datasetX = getDataset(state.xKey);
        const datasetY = getDataset(state.yKey);

        let sizeDataset = null;
        let sizeYearIndex = null;
        if (state.sizeKey !== AUTO_VALUE) {{
          sizeDataset = getDataset(state.sizeKey);
          sizeYearIndex = ensureDatasetHasYear(state.sizeKey, yearLabel);
        }}

        let colorDataset = null;
        let colorYearIndex = null;
        if (state.colorKey !== AUTO_VALUE) {{
          colorDataset = getDataset(state.colorKey);
          colorYearIndex = ensureDatasetHasYear(state.colorKey, yearLabel);
        }}

        const points = [];
        availableRegions.forEach((regionName) => {{
          const xSeries = datasetX.regions[regionName];
          const ySeries = datasetY.regions[regionName];
          if (!xSeries || !ySeries) {{
            return;
          }}
          const xValue = toNumber(xSeries[xYearIndex]);
          const yValue = toNumber(ySeries[yYearIndex]);
          if (xValue == null || yValue == null) {{
            return;
          }}
          if (state.logX && xValue <= 0) {{
            return;
          }}
          if (state.logY && yValue <= 0) {{
            return;
          }}

          let sizeValue = null;
          if (sizeDataset) {{
            const sizeSeries = sizeDataset.regions[regionName];
            if (sizeSeries) {{
              sizeValue = toNumber(sizeSeries[sizeYearIndex]);
            }}
          }}

          let colorValue = null;
          if (colorDataset) {{
            const colorSeries = colorDataset.regions[regionName];
            if (colorSeries) {{
              colorValue = toNumber(colorSeries[colorYearIndex]);
            }}
          }}

          points.push({{
            region: regionName,
            x: xValue,
            y: yValue,
            sizeValue,
            colorValue,
          }});
        }});

        if (points.length === 0) {{
          Plotly.purge("chart");
          statusMessage.textContent = "No numeric values available for the selected year.";
          return;
        }}

        function expandRange(values) {{
          const min = Math.min(...values);
          const max = Math.max(...values);
          if (min === max) {{
            const padding = Math.max(1, Math.abs(min) * 0.1);
            return [min - padding, max + padding];
          }}
          const span = max - min;
          const padding = span * 0.08;
          return [min - padding, max + padding];
        }}

        function computeSizes(values, useLog) {{
          const baseSize = 10;
          const minSize = 6;
          const maxSize = 28;
          const filtered = values.filter((value) => {{
            if (value == null) {{
              return false;
            }}
            if (useLog) {{
              return value > 0;
            }}
            return true;
          }});
          if (filtered.length === 0) {{
            return values.map(() => baseSize);
          }}
          const transformed = filtered.map((value) => (useLog ? Math.log10(value) : value));
          const min = Math.min(...transformed);
          const max = Math.max(...transformed);
          if (min === max) {{
            const constant = (minSize + maxSize) / 2;
            return values.map((value) => (value == null ? baseSize : constant));
          }}
          return values.map((value) => {{
            if (value == null) {{
              return baseSize;
            }}
            if (useLog && value <= 0) {{
              return baseSize;
            }}
            const transformedValue = useLog ? Math.log10(value) : value;
            const ratio = (transformedValue - min) / (max - min);
            return minSize + ratio * (maxSize - minSize);
          }});
        }}

        function ratioToColor(ratio) {{
          const clamped = Math.max(0, Math.min(1, ratio));
          const hue = 210 - clamped * 200;
          const lightness = 45 + clamped * 15;
          return `hsl(${{hue}}, 70%, ${{lightness}}%)`;
        }}

        function computeColors(values, useLog) {{
          const filtered = values.filter((value) => {{
            if (value == null) {{
              return false;
            }}
            if (useLog) {{
              return value > 0;
            }}
            return true;
          }});
          if (filtered.length === 0) {{
            return values.map(() => "#2563eb");
          }}
          const transformed = filtered.map((value) => (useLog ? Math.log10(value) : value));
          const min = Math.min(...transformed);
          const max = Math.max(...transformed);
          if (min === max) {{
            return values.map(() => "#2563eb");
          }}
          return values.map((value) => {{
            if (value == null) {{
              return "#2563eb";
            }}
            if (useLog && value <= 0) {{
              return "#2563eb";
            }}
            const transformedValue = useLog ? Math.log10(value) : value;
            const ratio = (transformedValue - min) / (max - min);
            return ratioToColor(ratio);
          }});
        }}

        const markerSizes = state.sizeKey === AUTO_VALUE
          ? new Array(points.length).fill(10)
          : computeSizes(points.map((point) => point.sizeValue), state.sizeLog);

        const markerColors = state.colorKey === AUTO_VALUE
          ? new Array(points.length).fill("#2563eb")
          : computeColors(points.map((point) => point.colorValue), state.colorLog);

        if (state.tracePaths) {{
          points.forEach((point) => {{
            if (!state.pathData[point.region]) {{
              state.pathData[point.region] = {{}};
            }}
            state.pathData[point.region][yearLabel] = {{
              x: point.x,
              y: point.y,
            }};
          }});
        }}

        const [xLower, xUpper] = expandRange(points.map((point) => point.x));
        const [yLower, yUpper] = expandRange(points.map((point) => point.y));

        const customdata = points.map((point) => [
          point.region,
          point.sizeValue,
          point.colorValue,
        ]);

        let hoverTemplate = "Region: %{{customdata[0]}}<br>X: %{{x}}<br>Y: %{{y}}";
        if (state.sizeKey !== AUTO_VALUE) {{
          hoverTemplate += "<br>Size: %{{customdata[1]}}";
        }}
        if (state.colorKey !== AUTO_VALUE) {{
          hoverTemplate += "<br>Colour: %{{customdata[2]}}";
        }}
        hoverTemplate += "<extra></extra>";

        const mainTrace = {{
          type: "scatter",
          mode: "markers",
          x: points.map((point) => point.x),
          y: points.map((point) => point.y),
          customdata,
          hovertemplate: hoverTemplate,
          marker: {{
            size: markerSizes,
            sizemode: "diameter",
            sizemin: 4,
            opacity: 0.9,
            color: markerColors,
            line: {{ width: 0.5, color: "#0f172a" }},
          }},
          showlegend: false,
        }};

        const pathTraces = [];
        if (state.tracePaths) {{
          Object.keys(state.pathData).forEach((regionName) => {{
            const entries = Object.entries(state.pathData[regionName]).map(([year, coords]) => ({{
              year,
              x: coords.x,
              y: coords.y,
            }}));
            const filteredEntries = entries.filter((entry) => {{
              if (entry.x == null || entry.y == null) {{
                return false;
              }}
              if (state.logX && entry.x <= 0) {{
                return false;
              }}
              if (state.logY && entry.y <= 0) {{
                return false;
              }}
              return true;
            }});
            if (filteredEntries.length < 2) {{
              return;
            }}
            filteredEntries.sort((a, b) => {{
              const aNumeric = Number(a.year);
              const bNumeric = Number(b.year);
              if (Number.isFinite(aNumeric) && Number.isFinite(bNumeric)) {{
                return aNumeric - bNumeric;
              }}
              return String(a.year).localeCompare(String(b.year));
            }});
            pathTraces.push({{
              type: "scatter",
              mode: "lines",
              x: filteredEntries.map((entry) => entry.x),
              y: filteredEntries.map((entry) => entry.y),
              name: regionName,
              line: {{
                width: 1,
                color: "rgba(148, 163, 184, 0.7)",
              }},
              hoverinfo: "skip",
              showlegend: false,
            }});
          }});
        }}

        Plotly.react("chart", [mainTrace, ...pathTraces], {{
          margin: {{ l: 80, r: 30, t: 20, b: 60 }},
          xaxis: {{
            title: resolveDatasetTitle(state.xKey),
            range: [xLower, xUpper],
            type: state.logX ? "log" : "linear",
            showgrid: true,
            gridcolor: "#e2e8f0",
            gridwidth: 1,
            zeroline: false,
          }},
          yaxis: {{
            title: resolveDatasetTitle(state.yKey),
            range: [yLower, yUpper],
            type: state.logY ? "log" : "linear",
            showgrid: true,
            gridcolor: "#e2e8f0",
            gridwidth: 1,
            zeroline: false,
          }},
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
      resetPathData();
      updateChartTitle();
      updateChart();
    }});

    yAxisSelect.addEventListener("change", () => {{
      state.yKey = yAxisSelect.value;
      ensureYearStateAvailable();
      resetPathData();
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

    sizeSelect.addEventListener("change", () => {{
      state.sizeKey = sizeSelect.value || AUTO_VALUE;
      updateLogToggleStates();
      updateChart();
    }});

    colorSelect.addEventListener("change", () => {{
      state.colorKey = colorSelect.value || AUTO_VALUE;
      updateLogToggleStates();
      updateChart();
    }});

    xAxisLogToggle.addEventListener("change", () => {{
      state.logX = xAxisLogToggle.checked;
      updateChart();
    }});

    yAxisLogToggle.addEventListener("change", () => {{
      state.logY = yAxisLogToggle.checked;
      updateChart();
    }});

    sizeLogToggle.addEventListener("change", () => {{
      state.sizeLog = sizeLogToggle.checked;
      updateChart();
    }});

    colorLogToggle.addEventListener("change", () => {{
      state.colorLog = colorLogToggle.checked;
      updateChart();
    }});

    tracePathsToggle.addEventListener("change", () => {{
      state.tracePaths = tracePathsToggle.checked;
      updateChart();
    }});

    clearPathsButton.addEventListener("click", () => {{
      resetPathData();
      updateChart();
    }});

    function init() {{
      buildAxisSelect(xAxisSelect, state.xKey);
      buildAxisSelect(yAxisSelect, state.yKey);
      buildSeriesSelect(sizeSelect, state.sizeKey, {{ includeAuto: true }});
      buildSeriesSelect(colorSelect, state.colorKey, {{ includeAuto: true }});
      updateLogToggleStates();
      tracePathsToggle.checked = state.tracePaths;
      ensureYearStateAvailable();
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

    def _determine_defaults(self) -> Dict[str, Optional[str]]:
        if not self._datasets:
            raise ValueError("ScatterPlot has no datasets to render.")

        x_key = self._resolve_dataset_key(self._default_x or next(iter(self._datasets)))
        y_key = (
            self._resolve_dataset_key(self._default_y)
            if self._default_y is not None
            else next((key for key in self._datasets if key != x_key), x_key)
        )

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

        size_key: Optional[str]
        if self._default_size is None:
            size_key = None
        else:
            size_key = self._resolve_dataset_key(self._default_size)
            if selected_year not in self._datasets[size_key].years:
                raise ValueError(
                    f"Dataset '{size_key}' does not contain year '{selected_year}' required for default size series."
                )

        color_key: Optional[str]
        if self._default_color is None:
            color_key = None
        else:
            color_key = self._resolve_dataset_key(self._default_color)
            if selected_year not in self._datasets[color_key].years:
                raise ValueError(
                    f"Dataset '{color_key}' does not contain year '{selected_year}' required for default colour series."
                )

        return {
            "x_key": x_key,
            "y_key": y_key,
            "year": selected_year,
            "size_key": size_key,
            "color_key": color_key,
        }

    def _compute_common_regions(self, dataset_x: _Dataset, dataset_y: _Dataset) -> List[str]:
        y_regions = set(dataset_y.regions.keys())
        common = [name for name in dataset_x.regions.keys() if name in y_regions]
        common.sort()
        return common

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


