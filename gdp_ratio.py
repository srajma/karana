import karana
from karana.loaders import load_owid_charts, load_imf_charts
from karana import series

INDIA_ADMINISTRATIONS = [
    {"start": 1947, "end": 1964, "PM": "Nehru", "party": "INC", "color": "#00AEEF"},
    {"start": 1964, "end": 1966, "PM": "Shastri", "party": "INC", "color": "#00AEEF"},
    {
        "start": 1966,
        "end": 1977,
        "PM": "Indira Gandhi",
        "party": "INC",
        "color": "#00AEEF",
    },
    {"start": 1977, "end": 1979, "PM": "Desai", "party": "JP", "color": "#FFC105"},
    {
        "start": 1979,
        "end": 1980,
        "PM": "Charan Singh",
        "party": "JP (S)",
        "color": "#FFC105",
    },
    {
        "start": 1980,
        "end": 1984,
        "PM": "Indira Gandhi",
        "party": "INC",
        "color": "#00AEEF",
    },
    {
        "start": 1984,
        "end": 1989,
        "PM": "Rajiv Gandhi",
        "party": "INC",
        "color": "#00AEEF",
    },
    {"start": 1989, "end": 1990, "PM": "VP Singh", "party": "JD", "color": "#FFC105"},
    {
        "start": 1990,
        "end": 1991,
        "PM": "Chandra Shekhar",
        "party": "SJP",
        "color": "#999999",
    },
    {
        "start": 1991,
        "end": 1996,
        "PM": "P.V. Narasimha Rao",
        "party": "INC",
        "color": "#00AEEF",
    },
    {"start": 1996, "end": 1997, "PM": "Deve Gowda", "party": "JD", "color": "#FFC105"},
    {"start": 1997, "end": 1998, "PM": "Gujral", "party": "JD", "color": "#FFC105"},
    {"start": 1998, "end": 2004, "PM": "Vajpayee", "party": "BJP", "color": "#FF7518"},
    {
        "start": 2004,
        "end": 2014,
        "PM": "Rg. Sonia Gandhi",
        "party": "INC",
        "color": "#00AEEF",
    },
    {
        "start": 2014,
        "end": 2024,
        "PM": "Narendra Modi",
        "party": "BJP",
        "color": "#FF7518",
    },
]


dfs = load_owid_charts(
    "gdp-per-capita-worldbank-constant-usd",
    "gdp-per-capita-maddison-project-database",
    "gdp-per-capita-penn-world-table",
    "gdp-per-capita-worldbank",
) | load_imf_charts("PPPPC.A", "PPPGDP.A", "NGDPD.A", "NGDPDPC.A")

page = karana.Plot("Per-capita income")

graph = karana.LineGraph(dfs)

graph.default_df("gdp-per-capita-penn-world-table")
graph.default_exp(series("India") / series("Indonesia"))
graph.administrations(INDIA_ADMINISTRATIONS)
# graph.titles(
#     {"terrorist-attacks": "Terrorist attacks", "terrorism-deaths": "Terrorism deaths"}
# )

page.add(graph)
page.html("<p class='note'>Between the charts</p>")
page.add(graph)

# graph.show("../maps/terrorism.html")
page.show("../maps/gdp_ratio_2.html")
