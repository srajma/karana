from copy import deepcopy
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
) | load_imf_charts("PPPPC.A", "NGDPRPPPPC.A", "NGDPDPC.A")

page = karana.Plot("Per-capita income")

graph_idn = karana.LineGraph(dfs)

graph_idn.default_df("gdp-per-capita-penn-world-table")
graph_idn.default_exp(series("India") / series("Indonesia"))
graph_idn.administrations(INDIA_ADMINISTRATIONS)
graph_idn.titles(
    {
        "gdp-per-capita-penn-world-table": "GDP/capita (PPP) [Penn World Table]",
        "gdp-per-capita-maddison-project-database": "GDP/capita (PPP) [Maddison Project Database]",
        "gdp-per-capita-worldbank": "GDP/capita (PPP) [World Bank]",
        "gdp-per-capita-worldbank-constant-usd": "GDP/capita (nominal) [World Bank]",
        "PPPPC.A": "GDP/capita (PPP, constant prices) [IMF WEO]",
        "NGDPRPPPPC.A": "GDP/capita (PPP, constant prices) [IMF WEO]",
        "NGDPDPC.A": "GDP/capita (nominal, current prices) [IMF WEO]",
    }
)

graph_sl = deepcopy(graph_idn)
graph_sl.default_exp(series("India") / series("Sri Lanka"))

graph_bgd = deepcopy(graph_idn)
graph_bgd.default_exp(series("India") / series("Bangladesh"))

graph_vnm = deepcopy(graph_idn)
graph_vnm.default_exp(series("India") / series("Vietnam"))

# graph_me = deepcopy(graph_idn)
# graph_me.default_df("NGDPDPC.A")
# graph_me.default_exp(series("India") / series("Middle East (Region)"))

# graph_sea = deepcopy(graph_me)
# graph_sea.default_exp(series("India") / series("Southeast Asia"))

# graph_ssa = deepcopy(graph_me)
# graph_ssa.default_exp(series("India") / series("Sub-Saharan Africa"))


# page.add(graph_sea)
# page.add(graph_ssa)
# page.add(graph_me)
page.add(graph_sl)
page.add(graph_vnm)
page.add(graph_idn)
page.add(graph_bgd)

# page.html("<p class='note'>Between the charts</p>")


# graph.show("../maps/terrorism.html")
page.show("../maps/gdp_ratio_2.html")
