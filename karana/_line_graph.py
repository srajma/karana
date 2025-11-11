from __future__ import annotations

import json
from collections.abc import Sequence as _Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import pandas as pd  # type: ignore

from ._expression import Expression


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

    @property
    def series_count(self) -> int:
        return len(self.regions)


class LineGraph:
    """
    Construct interactive HTML-based line graphs from multiple pandas dataframes.
    """

    def __init__(self, dfs: Mapping[str, pd.DataFrame]) -> None:
        if not dfs:
            raise ValueError("LineGraph requires at least one dataframe.")

        self._datasets: Dict[str, _Dataset] = {}
        for key, df in dfs.items():
            if not isinstance(df, pd.DataFrame):
                raise TypeError(f"Dataframe for key '{key}' must be a pandas DataFrame.")
            self._datasets[key] = self._convert_df(df, key)

        self._default_df: Optional[str] = None
        self._default_exprs: Optional[List[Expression]] = None
        self._administrations: Dict[str, List[dict[str, Any]]] = {}

    # --------------------------------------------------------------------- configuration

    def default_df(self, key: str) -> "LineGraph":
        if key not in self._datasets:
            raise KeyError(f"Unknown dataframe key '{key}'.")
        self._default_df = key
        return self

    def default_exp(self, *exprs: Expression) -> "LineGraph":
        if not exprs:
            raise ValueError("default_exp requires at least one expression.")

        if len(exprs) == 1:
            first = exprs[0]
            if isinstance(first, Expression):
                expr_list = [first]
            elif isinstance(first, _Sequence) and not isinstance(first, (str, bytes)):
                expr_list = list(first)
            else:
                raise TypeError(
                    "default_exp expects Expression instances (build with karana.series)."
                )
        else:
            expr_list = list(exprs)

        if not expr_list:
            raise ValueError("default_exp requires at least one expression.")

        for expr in expr_list:
            if not isinstance(expr, Expression):
                raise TypeError(
                    "default_exp expects Expression instances (build with karana.series)."
                )

        self._default_exprs = list(expr_list)
        return self

    def administrations(
        self,
        records: Sequence[Mapping[str, Any]],
        *,
        dataset: Optional[str] = None,
    ) -> "LineGraph":
        if not records:
            raise ValueError("administrations requires at least one record.")

        target_dataset = dataset or self._default_df or next(iter(self._datasets))
        if target_dataset not in self._datasets:
            raise KeyError(f"Unknown dataset key '{target_dataset}' for administrations().")

        processed: List[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, Mapping):
                raise TypeError("administrations expects a sequence of mapping objects.")

            try:
                raw_start = record["start"]
                raw_end = record["end"]
            except KeyError as exc:
                raise KeyError("administration records must include 'start' and 'end' values.") from exc

            start_year = _normalize_year(raw_start)
            end_year = _normalize_year(raw_end)
            if int(start_year) > int(end_year):
                raise ValueError(
                    f"Administration start year {start_year} exceeds end year {end_year}."
                )

            label = (
                record.get("label")
                or record.get("name")
                or record.get("title")
                or record.get("PM")
                or record.get("prime_minister")
            )
            party = record.get("party") or record.get("affiliation")
            color = record.get("color") or "#94a3b8"
            opacity = record.get("opacity")
            try:
                opacity_value = float(opacity) if opacity is not None else None
            except (TypeError, ValueError):
                raise ValueError(f"Invalid opacity value {opacity!r} for administration.") from None

            processed.append(
                {
                    "start": start_year,
                    "end": end_year,
                    "label": label,
                    "party": party,
                    "color": color,
                    "opacity": opacity_value,
                }
            )

        self._administrations[target_dataset] = processed
        return self

    # ------------------------------------------------------------------------------------

    def show(self, file_path: str, type: str = "html") -> Path:
        if type.lower() != "html":
            raise ValueError("Only HTML rendering is currently supported.")

        html = self._render_html()

        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        return output_path

    # ------------------------------------------------------------------------------------

    def _render_html(self) -> str:
        default_key, default_series_names, default_expressions = self._determine_defaults()

        payload = {
            "datasets": {
                key: {
                    "years": dataset.years,
                    "regions": dataset.regions,
                }
                for key, dataset in self._datasets.items()
            },
            "defaults": {
                "dataset": default_key,
                "seriesNames": default_series_names,
                "expressions": default_expressions,
            },
            "administrations": {
                key: self._administrations.get(key, [])
                for key in self._datasets.keys()
            },
        }

        payload_json = json.dumps(payload, ensure_ascii=False)

        # HTML/JS payload relies on simple DOM manipulation and Plotly for rendering.
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>karana LineGraph</title>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
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
    .karana-container {{
      max-width: 960px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
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
      margin-bottom: 1.5rem;
    }}
    .chart-and-legend {{
      display: flex;
      gap: 1.25rem;
      align-items: flex-start;
    }}
    .control-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
    }}
    label {{
      font-weight: 600;
      font-size: 0.95rem;
      min-width: 120px;
    }}
    select, input[type="text"] {{
      padding: 0.5rem 0.75rem;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
      font-size: 0.95rem;
      min-width: 220px;
      background: #f8fafc;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    select:focus, input[type="text"]:focus {{
      outline: none;
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
      background: white;
    }}
    button {{
      border: none;
      background: #2563eb;
      color: white;
      border-radius: 999px;
      padding: 0.45rem 0.9rem;
      font-size: 0.9rem;
      cursor: pointer;
      transition: background 0.2s ease, box-shadow 0.2s ease;
    }}
    button:hover {{
      background: #1d4ed8;
      box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
    }}
    .region-slot {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .region-slot span {{
      font-weight: 600;
      color: #475569;
      min-width: 1.5rem;
      text-align: right;
    }}
    .expression-list {{
      display: flex;
      flex-direction: column;
      width: 100%;
      gap: 0.5rem;
    }}
    .expression-slot {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      width: 100%;
    }}
    .expression-slot span {{
      font-weight: 600;
      color: #475569;
      min-width: 7rem;
    }}
    .expression-slot input {{
      flex: 1;
      min-width: 220px;
    }}
    .remove-expression,
    .remove-region {{
      background: #e11d48;
      padding: 0.35rem 0.7rem;
      border-radius: 999px;
      font-size: 0.85rem;
    }}
    .remove-expression:hover,
    .remove-region:hover {{
      background: #be123c;
    }}
    .status-message {{
      min-height: 1.25rem;
      font-size: 0.9rem;
      color: #dc2626;
    }}
    #chart {{
      flex: 1 1 0;
      min-height: 420px;
    }}
    .admin-legend {{
      width: 220px;
      background: #f8fafc;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      padding: 0.75rem;
      display: none;
    }}
    .admin-legend.is-visible {{
      display: flex;
      flex-direction: column;
      gap: 0.65rem;
    }}
    .admin-legend h2 {{
      font-size: 1rem;
      margin: 0 0 0.35rem;
      color: #1f2937;
    }}
    .admin-legend-item {{
      display: flex;
      gap: 0.6rem;
      align-items: center;
      font-size: 0.9rem;
      line-height: 1.2rem;
      color: #334155;
    }}
    .admin-legend-color {{
      width: 18px;
      height: 18px;
      border-radius: 4px;
      border: 2px dotted rgba(51, 65, 85, 0.4);
      flex-shrink: 0;
      position: relative;
    }}
    .admin-legend-color::after {{
      content: "";
      position: absolute;
      inset: 2px;
      border-radius: 2px;
      background: currentColor;
      opacity: 0.85;
    }}
    .admin-legend-text {{
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
    }}
    .admin-legend-title {{
      font-weight: 600;
      color: #111827;
    }}
    .admin-legend-subtitle {{
      font-size: 0.8rem;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <div class="karana-container">
    <h1>karana LineGraph</h1>
    <div class="controls">
      <div class="control-group">
        <label for="dataset-select">Dataset</label>
        <select id="dataset-select"></select>
      </div>
      <div class="control-group">
        <label>Series</label>
        <div id="region-selects" class="region-list"></div>
        <button id="add-region" type="button">+ Add Series</button>
      </div>
      <div class="control-group">
        <label>Expressions</label>
        <div id="expression-list" class="expression-list"></div>
        <button id="add-expression" type="button">+ Add Expression</button>
      </div>
      <div class="status-message" id="status-message"></div>
    </div>
    <div class="chart-and-legend">
      <div id="chart"></div>
      <div id="admin-legend" class="admin-legend"></div>
    </div>
  </div>

  <script>
    const payload = {payload_json};

    const state = {{
      datasetKey: payload.defaults.dataset,
      regionNames: [...payload.defaults.seriesNames],
      expressions: [...payload.defaults.expressions],
    }};

    const datasetSelect = document.getElementById("dataset-select");
    const regionContainer = document.getElementById("region-selects");
    const addRegionButton = document.getElementById("add-region");
    const expressionContainer = document.getElementById("expression-list");
    const addExpressionButton = document.getElementById("add-expression");
    const statusMessage = document.getElementById("status-message");
    const adminLegend = document.getElementById("admin-legend");

    function getDataset(key) {{
      return payload.datasets[key];
    }}

    function ensureRegionSelectionsAvailable(dataset) {{
      const available = Object.keys(dataset.regions);
      if (available.length === 0) {{
        throw new Error("Dataset '" + state.datasetKey + "' has no region data.");
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

    function buildDatasetSelect() {{
      const options = Object.keys(payload.datasets)
        .map((key) => {{
          const selected = key === state.datasetKey ? "selected" : "";
          return `<option value="${{key}}" ${{selected}}>${{key}}</option>`;
        }})
        .join("");
      datasetSelect.innerHTML = options;
      datasetSelect.value = state.datasetKey;
    }}

    function buildRegionControls() {{
      regionContainer.innerHTML = "";
      const dataset = getDataset(state.datasetKey);
      const available = Object.keys(dataset.regions);

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
      const dataset = getDataset(state.datasetKey);
      const available = Object.keys(dataset.regions);
      if (available.length === 0) {{
        statusMessage.textContent = "Cannot add series: dataset has no regions.";
        return;
      }}
      const unused = available.find((name) => !state.regionNames.includes(name));
      state.regionNames.push(unused || available[0]);
      buildRegionControls();
      updateChart();
    }}

    function removeRegionAt(index) {{
      state.regionNames.splice(index, 1);
      updateChart();
    }}

    function ensureExpressionsAvailable() {{
      if (!Array.isArray(state.expressions) || state.expressions.length === 0) {{
        state.expressions = ["1"];
      }}
    }}

    function buildAdministrationLegend(administrations) {{
      if (!adminLegend) {{
        return;
      }}

      if (!administrations || administrations.length === 0) {{
        adminLegend.classList.remove("is-visible");
        adminLegend.innerHTML = "";
        return;
      }}

      adminLegend.classList.add("is-visible");
      const header = document.createElement("h2");
      header.textContent = "Administrations";

      adminLegend.innerHTML = "";
      adminLegend.appendChild(header);

      administrations.forEach((admin) => {{
        const item = document.createElement("div");
        item.className = "admin-legend-item";

        const colorSwatch = document.createElement("span");
        colorSwatch.className = "admin-legend-color";
        colorSwatch.style.color = admin.color || "#94a3b8";
        item.appendChild(colorSwatch);

        const textWrapper = document.createElement("div");
        textWrapper.className = "admin-legend-text";

        const title = document.createElement("span");
        title.className = "admin-legend-title";
        const nameText = admin.label || admin.party || "Unnamed";
        title.textContent = nameText;
        textWrapper.appendChild(title);

        const partyPart = admin.label && admin.party ? " (" + admin.party + ")" : (admin.party || "");
        const rangePart = admin.start && admin.end ? String(admin.start) + " - " + String(admin.end) : "";
        const subtitleText = (partyPart || "") + ((partyPart && rangePart) ? " · " : "") + (rangePart || "");
        const trimmedSubtitle = subtitleText.trim();
        if (trimmedSubtitle) {{
          const subtitle = document.createElement("span");
          subtitle.className = "admin-legend-subtitle";
          subtitle.textContent = trimmedSubtitle;
          textWrapper.appendChild(subtitle);
        }}

        item.appendChild(textWrapper);
        adminLegend.appendChild(item);
      }});
    }}

    function expressionDisplayLabel(expression, regionSeries) {{
      const tokens = tokenize(expression);
      const parts = tokens.map((token) => {{
        if (token === "(" || token === ")" || "+-*/".includes(token)) {{
          return token;
        }}
        const numeric = Number(token);
        if (!token.includes(".") && !Number.isNaN(numeric)) {{
          const idx = numeric - 1;
          if (idx >= 0 && idx < regionSeries.length) {{
            return regionSeries[idx].name;
          }}
        }}
        return token;
      }});
      let label = parts.join(" ");
      label = label.replace(/\\s+([)])/g, "$1");
      label = label.replace(/([(])\\s+/g, "$1");
      label = label.replace(/\\s*([+\\-*/])\\s*/g, " $1 ");
      return label.replace(/\\s+/g, " ").trim();
    }}

    function buildExpressionControls() {{
      ensureExpressionsAvailable();
      expressionContainer.innerHTML = "";

      state.expressions.forEach((exprText, idx) => {{
        const slot = document.createElement("div");
        slot.className = "expression-slot";

        const label = document.createElement("span");
        label.textContent = `Expression ${{idx + 1}}`;
        slot.appendChild(label);

        const input = document.createElement("input");
        input.type = "text";
        input.placeholder = "e.g. 1/(1+2)";
        input.value = exprText;
        input.addEventListener("input", () => {{
          state.expressions[idx] = input.value;
          updateChart();
        }});
        slot.appendChild(input);

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "remove-expression";
        remove.textContent = "Remove";
        remove.title = "Remove expression";
        remove.addEventListener("click", () => {{
          if (state.expressions.length <= 1) {{
            statusMessage.textContent = "At least one expression is required.";
            return;
          }}
          state.expressions.splice(idx, 1);
          buildExpressionControls();
          updateChart();
        }});
        slot.appendChild(remove);

        expressionContainer.appendChild(slot);
      }});
    }}

    function tokenize(expression) {{
      const tokens = [];
      let i = 0;
      while (i < expression.length) {{
        const ch = expression[i];
        if (ch === " " || ch === "\\t" || ch === "\\n") {{
          i += 1;
          continue;
        }}
        if ("+-*/()".includes(ch)) {{
          tokens.push(ch);
          i += 1;
          continue;
        }}
        if ((ch >= "0" && ch <= "9") || ch === ".") {{
          let value = ch;
          i += 1;
          while (i < expression.length) {{
            const next = expression[i];
            if ((next >= "0" && next <= "9") || next === ".") {{
              value += next;
              i += 1;
            }} else {{
              break;
            }}
          }}
          tokens.push(value);
          continue;
        }}
        throw new Error("Unexpected character '" + ch + "' in expression.");
      }}
      return tokens;
    }}

    function shuntingYard(tokens, regionCount) {{
      const output = [];
      const operators = [];
      const precedence = {{
        "+": 1,
        "-": 1,
        "*": 2,
        "/": 2,
        "u-": 3,
      }};
      const associativity = {{
        "+": "L",
        "-": "L",
        "*": "L",
        "/": "L",
        "u-": "R",
      }};
      let expectOperand = true;

      for (const token of tokens) {{
        if (token === "(") {{
          operators.push(token);
          expectOperand = true;
          continue;
        }}
        if (token === ")") {{
          while (operators.length > 0 && operators[operators.length - 1] !== "(") {{
            output.push(operators.pop());
          }}
          if (operators.length === 0) {{
            throw new Error("Mismatched parentheses in expression.");
          }}
          operators.pop();
          expectOperand = false;
          continue;
        }}
        if ("+-*/".includes(token)) {{
          if (token === "-" && expectOperand) {{
            operators.push("u-");
            continue;
          }}
          while (operators.length > 0) {{
            const top = operators[operators.length - 1];
            if (top === "(") {{
              break;
            }}
            const topPrec = precedence[top];
            const tokenPrec = precedence[token];
            if (
              topPrec > tokenPrec ||
              (topPrec === tokenPrec && associativity[token] === "L")
            ) {{
              output.push(operators.pop());
            }} else {{
              break;
            }}
          }}
          operators.push(token);
          expectOperand = true;
          continue;
        }}
        // number literal (potentially region reference)
        const numeric = Number(token);
        if (Number.isNaN(numeric)) {{
          throw new Error("Invalid number token '" + token + "'.");
        }}
        if (!token.includes(".") && numeric >= 1 && numeric <= regionCount) {{
          output.push({{ type: "region", index: numeric - 1 }});
        }} else {{
          output.push({{ type: "literal", value: numeric }});
        }}
        expectOperand = false;
      }}

      while (operators.length > 0) {{
        const op = operators.pop();
        if (op === "(" || op === ")") {{
          throw new Error("Mismatched parentheses in expression.");
        }}
        output.push(op);
      }}

      return output;
    }}

    function toArray(value, length) {{
      if (Array.isArray(value)) {{
        return value.slice();
      }}
      const arr = new Array(length);
      for (let i = 0; i < length; i += 1) {{
        arr[i] = value;
      }}
      return arr;
    }}

    function evaluateExpression(expression, regionSeries, yearsCount) {{
      const tokens = tokenize(expression);
      const rpn = shuntingYard(tokens, regionSeries.length);
      const stack = [];

      for (const token of rpn) {{
        if (typeof token === "string") {{
          if (token === "u-") {{
            if (stack.length < 1) {{
              throw new Error("Invalid expression: unary operator missing operand.");
            }}
            const value = stack.pop();
            const array = toArray(value, yearsCount);
            stack.push(array.map((v) => (v == null ? null : -v)));
            continue;
          }}
          if (stack.length < 2) {{
            throw new Error("Invalid expression: binary operator missing operands.");
          }}
          const right = stack.pop();
          const left = stack.pop();
          const leftArr = toArray(left, yearsCount);
          const rightArr = toArray(right, yearsCount);
          const result = new Array(yearsCount);
          for (let i = 0; i < yearsCount; i += 1) {{
            const lv = leftArr[i];
            const rv = rightArr[i];
            if (lv == null || rv == null) {{
              result[i] = null;
              continue;
            }}
            switch (token) {{
              case "+":
                result[i] = lv + rv;
                break;
              case "-":
                result[i] = lv - rv;
                break;
              case "*":
                result[i] = lv * rv;
                break;
              case "/":
                result[i] = rv === 0 ? null : lv / rv;
                break;
              default:
                throw new Error("Unsupported operator '" + token + "'.");
            }}
          }}
          stack.push(result);
          continue;
        }}
        if (token.type === "region") {{
          const idx = token.index;
          if (idx < 0 || idx >= regionSeries.length) {{
            throw new Error("Expression references series #" + (idx + 1) + " which is undefined.");
          }}
          stack.push(regionSeries[idx].values);
          continue;
        }}
        if (token.type === "literal") {{
          stack.push(token.value);
          continue;
        }}
        throw new Error("Unknown token in evaluation.");
      }}

      if (stack.length !== 1) {{
        throw new Error("Invalid expression: leftover values after evaluation.");
      }}

      return toArray(stack[0], yearsCount);
    }}

    function updateChart() {{
      try {{
        statusMessage.textContent = "";
        const dataset = getDataset(state.datasetKey);
        ensureRegionSelectionsAvailable(dataset);
        ensureExpressionsAvailable();
        buildRegionControls();

        const years = dataset.years;
        const numericYears = years.map((year) => {{
          const value = Number(year);
          return Number.isNaN(value) ? null : value;
        }});
        const useNumericYears = numericYears.every((value) => value !== null);
        const baseXValues = useNumericYears ? numericYears : years;
        const regionSeries = state.regionNames.map((name, idx) => {{
          const values = dataset.regions[name];
          if (!values) {{
            throw new Error("Region '" + name + "' not available in dataset.");
          }}
          return {{
            index: idx,
            name,
            values,
          }};
        }});

        const administrations = (payload.administrations && payload.administrations[state.datasetKey]) || [];

        const trimmedExpressions = state.expressions.map((expr) => expr.trim());
        if (trimmedExpressions.some((expr) => expr.length === 0)) {{
          throw new Error("Expressions cannot be empty.");
        }}

        const traces = trimmedExpressions.map((exprText, idx) => {{
          const values = evaluateExpression(exprText, regionSeries, years.length);
          const label = expressionDisplayLabel(exprText, regionSeries) || `Expression ${{idx + 1}}`;
          return {{
            x: baseXValues,
            y: values,
            mode: "lines",
            name: label,
            line: {{
              width: 3,
            }},
            hovertemplate: `%{{x}}<br>${{label}}: %{{y}}<extra></extra>`,
          }};
        }});

        const availabilityMask = new Array(baseXValues.length).fill(false);
        traces.forEach((trace) => {{
          trace.y.forEach((value, index) => {{
            if (value != null && Number.isFinite(value)) {{
              availabilityMask[index] = true;
            }}
          }});
        }});

        let sliceStartIndex = availabilityMask.indexOf(true);
        let sliceEndIndex = availabilityMask.lastIndexOf(true);
        if (sliceStartIndex === -1 || sliceEndIndex === -1) {{
          sliceStartIndex = 0;
          sliceEndIndex = baseXValues.length - 1;
        }}

        const trimmedXValues = baseXValues.slice(sliceStartIndex, sliceEndIndex + 1);
        traces.forEach((trace) => {{
          trace.x = trace.x.slice(sliceStartIndex, sliceEndIndex + 1);
          trace.y = trace.y.slice(sliceStartIndex, sliceEndIndex + 1);
        }});

        const hasTrimmedDomain = trimmedXValues.length > 0;
        const xRangeMin = hasTrimmedDomain ? trimmedXValues[0] : baseXValues[0];
        const xRangeMax = hasTrimmedDomain
          ? trimmedXValues[trimmedXValues.length - 1]
          : baseXValues[baseXValues.length - 1];

        const xAxisConfig = {{ title: "Year" }};
        if (useNumericYears) {{
          xAxisConfig.type = "linear";
          xAxisConfig.tickformat = "d";
        }} else {{
          xAxisConfig.type = "category";
        }}
        if (hasTrimmedDomain) {{
          xAxisConfig.range = [xRangeMin, xRangeMax];
        }}

        const toNumericOrNull = (value) => {{
          const numeric = Number(value);
          return Number.isNaN(numeric) ? null : numeric;
        }};

        const rectangles = administrations
          .map((admin) => {{
            const fillcolor = admin.color || "#94a3b8";
            const opacity = typeof admin.opacity === "number" ? admin.opacity : 0.12;
            if (useNumericYears) {{
              const startNumeric = toNumericOrNull(admin.start);
              const endNumeric = toNumericOrNull(admin.end);
              if (startNumeric == null || endNumeric == null) {{
                return null;
              }}
              if (startNumeric > xRangeMax || endNumeric < xRangeMin) {{
                return null;
              }}
              return {{
                type: "rect",
                xref: "x",
                yref: "paper",
                x0: Math.max(startNumeric, xRangeMin),
                x1: Math.min(endNumeric, xRangeMax),
                y0: 0,
                y1: 1,
                fillcolor,
                opacity,
                line: {{ width: 0 }},
                layer: "below",
              }};
            }}

            return {{
              type: "rect",
              xref: "x",
              yref: "paper",
              x0: admin.start,
              x1: admin.end,
              y0: 0,
              y1: 1,
              fillcolor,
              opacity,
              line: {{ width: 0 }},
              layer: "below",
            }};
          }})
          .filter(Boolean);

        const boundaryLines = [];
        const seenBoundaries = new Set();
        const addBoundary = (value, key, color) => {{
          if (value == null) {{
            return;
          }}
          if (seenBoundaries.has(key)) {{
            return;
          }}
          seenBoundaries.add(key);
          boundaryLines.push({{
            type: "line",
            xref: "x",
            yref: "paper",
            x0: value,
            x1: value,
            y0: 0,
            y1: 1,
            line: {{ color, width: 2, dash: "dot" }},
            layer: "above",
          }});
        }};

        administrations.forEach((admin) => {{
          const color = admin.color || "#94a3b8";
          if (useNumericYears) {{
            const startNumeric = toNumericOrNull(admin.start);
            const endNumeric = toNumericOrNull(admin.end);
            if (startNumeric != null && startNumeric >= xRangeMin && startNumeric <= xRangeMax) {{
              addBoundary(startNumeric, "start-" + startNumeric, color);
            }}
            if (endNumeric != null && endNumeric >= xRangeMin && endNumeric <= xRangeMax) {{
              addBoundary(endNumeric, "end-" + endNumeric, color);
            }}
            return;
          }}

          addBoundary(admin.start, "start-" + admin.start, color);
          addBoundary(admin.end, "end-" + admin.end, color);
        }});

        const yValues = [];
        traces.forEach((trace) => {{
          trace.y.forEach((v) => {{
            if (v != null && Number.isFinite(v)) {{
              yValues.push(v);
            }}
          }});
        }});

        let yAxisConfig;
        if (yValues.length === 0) {{
          yAxisConfig = {{ title: "Value", autorange: true }};
        }} else {{
          const minValue = Math.min(...yValues);
          const maxValue = Math.max(...yValues);
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
          yAxisConfig = {{ title: "Value", range: [lower, upper], autorange: false }};
        }}

        buildAdministrationLegend(administrations);

        Plotly.react("chart", traces, {{
          margin: {{ l: 60, r: 30, t: 20, b: 60 }},
          hovermode: "x unified",
          legend: {{ orientation: "h", y: -0.2 }},
          xaxis: xAxisConfig,
          yaxis: yAxisConfig,
          shapes: [...rectangles, ...boundaryLines],
        }});
      }} catch (error) {{
        statusMessage.textContent = error.message;
        Plotly.purge("chart");
      }}
    }}

    datasetSelect.addEventListener("change", () => {{
      state.datasetKey = datasetSelect.value;
      const dataset = getDataset(state.datasetKey);
      ensureRegionSelectionsAvailable(dataset);
      buildRegionControls();
      buildExpressionControls();
      updateChart();
    }});

    addRegionButton.addEventListener("click", () => {{
      addRegionSlot();
    }});

    addExpressionButton.addEventListener("click", () => {{
      ensureExpressionsAvailable();
      state.expressions.push("1");
      buildExpressionControls();
      updateChart();
    }});

    function init() {{
      buildDatasetSelect();
      const dataset = getDataset(state.datasetKey);
      ensureRegionSelectionsAvailable(dataset);
      buildRegionControls();
      buildExpressionControls();
      updateChart();
    }}

    init();
  </script>
</body>
</html>
"""
        return html

    def _determine_defaults(self) -> tuple[str, List[str], List[str]]:
        default_key = self._default_df or next(iter(self._datasets))
        dataset = self._datasets[default_key]
        if not dataset.regions:
            raise ValueError(f"Dataset '{default_key}' has no regions to plot.")

        if self._default_exprs is None:
            first_region = next(iter(dataset.regions))
            series_names = [first_region]
            expression_texts = ["1"]
        else:
            series_names: List[str] = []
            seen: set[str] = set()
            for expr in self._default_exprs:
                for name in expr.collect_series():
                    if name not in seen:
                        seen.add(name)
                        series_names.append(name)
            if not series_names:
                raise ValueError("default_exp expressions must reference at least one series.")
            missing = [name for name in series_names if name not in dataset.regions]
            if missing:
                missing_str = ", ".join(missing)
                raise KeyError(
                    f"Series referenced in default expression not found in default dataset '{default_key}': {missing_str}"
                )
            expression_texts = [
                expr.to_placeholder_expression(series_names) for expr in self._default_exprs
            ]

        return default_key, series_names, expression_texts

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


