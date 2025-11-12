## sample usage

```python
import karana
from karana.loaders import load_owid_charts
from karana import series

# for marking boundaries
INDIA_ADMINISTRATIONS = [
    {"start": 1947, "end": 1964, "PM": "Nehru", "party": "INC", "color": "#00AEEF"},
    {"start": 1964, "end": 1966, "PM": "Shastri", "party": "INC", "color": "#00AEEF"},
    {"start": 1966, "end": 1977, "PM": "Indira Gandhi", "party": "INC", "color": "#00AEEF"},
    {"start": 1977, "end": 1979, "PM": "Desai", "party": "JP", "color": "#FFC105"},
    {"start": 1979, "end": 1980, "PM": "Charan Singh", "party": "JP (S)", "color": "#FFC105"},
    {"start": 1980, "end": 1984, "PM": "Indira Gandhi", "party": "INC", "color": "#00AEEF"},
    {"start": 1984, "end": 1989, "PM": "Rajiv Gandhi", "party": "INC", "color": "#00AEEF"},
    {"start": 1989, "end": 1990, "PM": "VP Singh", "party": "JD", "color": "#FFC105"},
    {"start": 1990, "end": 1991, "PM": "Chandra Shekhar", "party": "SJP", "color": "#999999"},
    {"start": 1991, "end": 1996, "PM": "P.V. Narasimha Rao", "party": "INC", "color": "#00AEEF"},
    {"start": 1996, "end": 1997, "PM": "Deve Gowda", "party": "JD", "color": "#FFC105"},
    {"start": 1997, "end": 1998, "PM": "Gujral", "party": "JD", "color": "#FFC105"},
    {"start": 1998, "end": 2004, "PM": "Vajpayee", "party": "BJP", "color": "#FF7518"},
    {"start": 2004, "end": 2014, "PM": "Rg. Sonia Gandhi", "party": "INC", "color": "#00AEEF"},
    {"start": 2014, "end": 2024, "PM": "Narendra Modi", "party": "BJP", "color": "#FF7518"}
]

# load datasets from Our World In Data (OWID)
# use the slug of any URL under /grapher/,
# e.g. https://ourworldindata.org/grapher/life-expectancy -> "life-expectancy"
# you can also click the download button on an OWID chart on another page to find its exclusive slug
dfs = load_owid_charts("terrorist-attacks", "terrorism-deaths")

# to have multiple graphs on one page, define a Plot and add Graphs to it.
# otherwise, you can also just create a LineGraph and use its show("...") method directly
page = karana.Plot("Terrorism trends")

# create line graph
graph = karana.LineGraph(dfs)
graph.default_df("terrorism-deaths") # default dataset from dropdown to show
graph.default_exp(series("India") / series("World")) # some arithmetical expression of series
graph.default_scale("log") # optional: start charts in logarithmic mode
graph.administrations(INDIA_ADMINISTRATIONS) # add administrations

# optional: titles to give for each displayed chart
graph.titles({"terrorist-attacks": "Terrorist attacks", "terrorism-deaths": "Terrorism deaths"})

page.add(graph)
page.html("<p class='note'>Custom HTML between the charts</p>")
page.add(graph) # add another graph; here we're just adding another copy of the same

# graph.show("../maps/terrorism.html") # to export a Graph directly rather than a Plot
page.show("../maps/terrorism.html")
```

### scatter plots

```python
from karana import ScatterPlot
from karana.loaders import load_owid_charts

datasets = load_owid_charts(
    "life-expectancy",
    "gdp-per-capita-maddison-project-database",
    "population",
    "children-born-per-woman",
)

scatter = ScatterPlot(datasets)
scatter.default_axes(
    x="gdp-per-capita-maddison-project-database:gdp_per_capita_maddison_project_database",
    y="life-expectancy:life_expectancy",
)
scatter.default_size("population:population")
scatter.default_color("children-born-per-woman:children_born_per_woman")
scatter.default_year(2019)
scatter.show("test_outputs/life_vs_gdp_scatter.html")
```

The generated page includes dropdowns for X/Y axis datasets, optional size or colour series (with “Auto” preserving defaults), logarithmic toggles for each scale, and a “Trace out point paths” option that connects each region’s historical position across years.

## dataframes

The dataframe format supported is a pandas dataframe with columns: `Region, (year number), (year number), ...`. There are built-in data loaders `load_owid_charts()` (for OurWorldInData data) and `load_imf_charts()` (for IMF World Economic Outlook data).

### data sources:

OWID: https://docs.owid.io/projects/etl/api/chart-api/

IMF WEO: https://data.imf.org/en/datasets/IMF.RES:WEO

Special GDP/capita (nominal) [IMF WEO] data (`data/imf_weo_ngdpdpc.csv`) downloaded from https://www.imf.org/external/datamapper/NGDPDPC@WEO and exported to csv