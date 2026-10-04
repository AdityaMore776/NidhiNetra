"""By-eye labels for the owner's "simple and certain" pivot (T099 Cost, T100 Duplicate), read
3 Oct 2026 on the eSAKSHI dashboard's 40,935 works. Work ids only; the reasons name no person.

COST_RECORD_ABOVE: every real work whose RECORD alone puts its price per unit above the Cost
engine's question line (more than 25% above the 98th percentile of a tight group of the same
standard item in its district or state; data/trial/simple_certain_trial.py lists them):
  "price"    a real price question: one stated item, one site, the price high
  "misread"  the record's count is wrong for the money (two lights listed as "1", several sites)
  "spec"     a bigger or different item the record does not price as one (a 16 m mast, a
             "4 way" light, a solar mini-mast compared with grid masts)
  "grey"     nothing in the record explains it, nothing confirms it

SPLIT_GROUPS: every group the Duplicate check's strictest split rule finds on the dashboard
(agents/dup_split/repeat.py: 2-5 alike pieces at one place or numbered parts, one MP, within 30
days, every piece 96-100% of the Rs 5 or 10 lakh limit, the total above it):
  "yes"   one job cut into pieces to stay under the limit (reach-1 / reach-2, four rooms of one
          school, Sy.No 488 / 488-A / B / C of one road, a 4-plant project as 4 works)
  "grey"  two pieces that could be two jobs (left and right side of one bridge approach; "CC
          roads in various localities" of one ward, twice)
  "no"    not one job

REPEAT_DASHBOARD_PAIRS: the 25 pairs of the strictest text rule (same work type, same district,
descriptions 90%+ alike, every place word shared, no number, side, gender or continuation word
apart, not a series of 3+ copies, not "various places") whose dates are more than 60 days apart:
  "same"       reads as the same asset at the same site funded twice: worth checking
  "grey"       could be one asset or two (a village's lights, one landmark, "completion of")
  "different"  no site named, a different colony or site, generic words only
"""

COST_RECORD_ABOVE = {
    # in-sample (the reference from every year)
    "WS/MP18176/2024-2025/142537": "grey",      # one high mast at a bus stand, no height stated
    "WS/MP18228/2025-2026/159704": "misread",   # two people's houses listed, "1 nag" each
    "WS/MP18228/2025-2026/159716": "misread",   # the same pattern
    "WS/MP18230/2025-2026/161094": "spec",      # "4 way" solar lights: four lamps per pole
    "WS/MP18377/2025-2026/269534": "misread",   # a list of several sites read as two masts
    # hold-out (reference before 2026, works of 2026)
    "WS/MP755/2025-2026/197519": "spec",        # a 16 m high mast
    "WS/MP755/2025-2026/246198": "spec",        # a "mini" high mast
    "WS/MP858/2024-2025/168926": "misread",     # six sites and a 9 m mast in one record
    "WS/MP858/2025-2026/227591": "misread",     # 2 + 2 + 2 masts read as 2
    "WS/MP18244/2025-2026/210024": "spec",      # a solar mini-mast with six 60 W lights,
    "WS/MP18244/2025-2026/210026": "spec",      # compared with grid high masts (six records
    "WS/MP18244/2025-2026/210027": "spec",      # of one design at six sites)
    "WS/MP18244/2025-2026/210028": "spec",
    "WS/MP18244/2025-2026/210029": "spec",
    "WS/MP18244/2025-2026/210030": "spec",
}

REPEAT_DASHBOARD_PAIRS = {
    ("NOID-4599b175", "WS/MP18095/2025-2026/208344"): "same",
    ("WS/MP18276/2025-2026/184966", "WS/MP18276/2025-2026/184967"): "different",
    ("WS/MP422/2025-2026/141663", "WS/MP422/2024-2025/141664"): "different",
    ("WS/MP457/2025-2026/201109", "WS/MP457/2025-2026/253549"): "same",
    ("WS/MP18178/2024-2025/174396", "WS/MP18178/2025-2026/202124"): "same",
    ("WS/MP372/2025-2026/253232", "WS/MP372/2026-2027/283906"): "grey",
    ("NOID-f734d61e", "WS/MP370/2024-2025/166463"): "grey",
    ("WS/MP18011/2024-2025/173515", "WS/MP18011/2025-2026/207053"): "same",
    ("WS/MP18011/2024-2025/173514", "WS/MP18011/2025-2026/207053"): "different",
    ("WS/MP18011/2024-2025/173496", "WS/MP18011/2025-2026/207042"): "different",
    ("WS/MP18114/2025-2026/157492", "WS/MP18114/2025-2026/166011"): "same",
    ("WS/MP18157/2024-2025/163245", "WS/MP18157/2025-2026/236878"): "same",
    ("WS/MP18338/2025-2026/151990", "WS/MP18338/2024-2025/152413"): "grey",
    ("WS/MP18157/2025-2026/188692", "WS/MP18157/2025-2026/198815"): "grey",
    ("WS/MP18184/2025-2026/171660", "WS/MP18184/2025-2026/171253"): "different",
    ("WS/MP18184/2025-2026/171660", "WS/MP18184/2025-2026/171252"): "different",
    ("WS/MP18184/2025-2026/171661", "WS/MP18184/2025-2026/171253"): "different",
    ("WS/MP18184/2025-2026/171661", "WS/MP18184/2025-2026/171252"): "different",
    ("WS/MP18149/2025-2026/182818", "WS/MP18149/2025-2026/184444"): "grey",
    ("WS/MP641/2024-2025/153873", "WS/MP641/2025-2026/179569"): "same",
    ("WS/MP761/2024-2025/149051", "WS/MP761/2024-2025/170683"): "grey",
    ("WS/MP18321/2025-2026/187965", "WS/MP18321/2025-2026/187964"): "different",
    ("WS/MP18335/2025-2026/210206", "WS/MP18335/2025-2026/210207"): "different",
    ("WS/MP005/2025-2026/196998", "WS/MP005/2025-2026/175161"): "same",
    ("WS/MP18155/2024-2025/163661", "WS/MP18155/2025-2026/198948"): "different",
}

SPLIT_GROUPS = {
    "G-WS/MP18003/2024-2025/157517": "yes",     # one hill road, Sy.No 488 / 488-A / B / C
    "G-WS/MP18006/2024-2025/135640": "yes",     # underground drainage, Reach I / II / III
    "G-WS/MP18009/2024-2025/161192": "yes",     # street lighting of one ward, twice
    "G-WS/MP18009/2024-2025/163081": "yes",     # one road, reach-1 / reach-2
    "G-WS/MP18009/2024-2025/163087": "yes",     # one road, reach-1 / reach-2
    "G-WS/MP18138/2024-2025/148109": "yes",     # one road upgradation, twice
    "G-WS/MP18351/2024-2025/158085": "yes",     # "the project involves 04 plants", as 4 works
    "G-WS/MP18351/2024-2025/160019": "yes",     # internal CC roads Bit1 / Bit2
    "G-WS/MP18393/2024-2025/151997": "grey",    # "CC roads in various localities", twice
    "G-WS/MP405/2024-2025/149697": "yes",       # one road, reach-1 / reach-2
    "G-WS/MP526/2024-2025/147539": "grey",      # left / right side of one bridge approach
    "G-WS/MP526/2024-2025/147605": "yes",       # one road's gravelling, Reach-1 / Reach-2
    "G-WS/MP526/2026-2027/152486": "yes",       # one drain, segments I & II / III & V
    "G-WS/MP574/2025-2026/145476": "yes",       # four new rooms of one school
}
