import karana
import karana.loaders.owid as owid

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


terror_attacks = owid.load_chart("terrorist-attacks")
terrorism_deaths = owid.load_chart("terrorism-deaths")

# graph = karana.LineGraph({
#     "terror-attacks": terror_attacks,
#     "terrorism-deaths": terrorism_deaths,
# })

# graph.default_df("terror-attacks")
# graph.administrations(INDIA_ADMINISTRATIONS)

# graph.show("terrorism.html")
print(terror_attacks)