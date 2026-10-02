"""By-eye labels for the eSAKSHI dashboard trial (dashboard_trial.py), read 2 Oct 2026.

Read by the agent (Claude Code) working for @AdityaMore776, one work at a time, from the masked
description, amount, dates and the engine's reasons, with the meanings the team uses:

  yes   worth an officer's look: the question the engine asks is a real one for this work
  grey  an officer could reasonably look (maintenance-like, two lights at one house, a letter
        number for a description)
  no    the engine misread the record (a road named after a temple; the same spec sheet read
        as "the same place"; different places under one block name)

QUEUE_BASELINE      40 random review-queue works of the BASELINE engines (results/
                    dashboard_baseline_queue.csv, seed 1002): 38 yes (two of them only mildly:
                    an urban road at Rs 20-32 lakh waiting about two years), 1 grey (a municipal
                    garden at Rs 38 lakh), 1 no (two "High must light" works read as one place
                    because the typo "must" looked like a place). 11 of the 40 are one Rs 1.53
                    crore street-light purchase filed as 11 works, 4 one bus-shed batch, 3 one
                    sabhamandap batch: 25 distinct cases.
R07                 12 random R07 flags of the baseline (dashboard_baseline_codes.csv): 7 yes,
                    2 grey, 3 no (2 roads named after a temple / church, 1 shed "near" a temple
                    courtyard). All 3 "no" are no longer flagged by the 2 Oct reader; on all
                    40,935 works it dropped exactly those kinds (4) and added 1 real temple work.
SPLIT_AT_ONE_SITE   12 random same-site splits of the baseline: 5 yes, 4 grey, 3 no (different
                    places under one block name; a spec sheet; Tamil words for "stage" read as a
                    place). The 2 Oct generic words and "different place" reading remove all 3.
REPEATED_WHILE_OPEN the 7 baseline repeat flags: 2 yes, 1 grey, 4 no (one solar-light spec sheet,
                    amounts 71% apart).
R14                 12 random R14 flags (dashboard_v2engines_codes.csv): 12 yes: constructions
                    recorded complete 0-7 days after a sanction that came months after the
                    recommendation; the dates need checking in every case.
QUEUE_V3            40 random review-queue works with every 2 Oct 2026 change and fusion v3
                    (results/dashboard_v3_queue.csv, seed 1002; the queue is 419 works, 9x the
                    baseline's 47): 37 yes, 1 grey (the same municipal garden), 2 no, both R07
                    misreads fixed the same day ("Pulic Distribution shop" is a ration shop; a
                    "Memorial Institution" named after a person is a school). By finding: R12 18
                    of 18, R14 13 of 13, R07 4 of 6 (the 2 fixed), stretches 2 of 2.
R07_CHANGES         every work whose R07 answer differs between main's reader and the final
                    2 Oct 2026 reader on all 40,935 works (results/dashboard_baseline_flags.json
                    vs dashboard_final_flags.json; main 54 flags, final 63): the 15 gained are
                    all yes (a church toilet, a wall for a temple, a hall in a temple, a temple's
                    beautification, a solar plant in a private ITI, 10 works "table of kitchen,
                    private school"); of the 6 dropped, 5 were misreads (2 roads named after a
                    temple / church, a ration shop, a school, a shed "near" a temple courtyard)
                    and 1 grey (a platform "beside" a temple campus).
QUEUE_FINAL         40 random review-queue works of the final code (results/
                    dashboard_final_queue.csv, seed 1002; queue 427): 39 yes, 1 grey (Rs 26 lakh
                    whose description is only "as per recommendation letter attached"), 0 no. By
                    finding: R12 20 of 21 (+1 grey), R14 13 of 13, R07 3 of 3, splits and
                    stretches 3 of 3.
COST_SAMPLE         the 12 random Cost flags of the final run (dashboard_final_codes.csv,
                    statistical:COST_ABOVE_PEERS), read 2 Oct 2026 for T056: 3 yes (a Rs 47
                    lakh PCC road with no length; Rs 6.76 lakh of street lights "near a temple"
                    with no count; Rs 36.6 lakh "Solar Street Lights"), 5 grey (a latrine and a
                    wall in one work; "community centers and halls"; a road with wing walls; a
                    hall at a burial ground; a night shelter typed OTHER), 4 no: one amount for
                    several streets ("2nd 3rd 4th 7th Cross", "Street & Streets"), a list of
                    park components, solar panels for a library typed as street lights.
COST_CHANGES        every Cost flag that changed when one amount for several streets became a
                    bundle (scope.several_ways, T056; dashboard_final_flags.json vs
                    dashboard_agents2_flags.json): 7 dropped, all rightly (4 several streets, 3
                    vague sums R12 still flags); 2 gained through the narrower peer bands: 1
                    grey (a Rs 27.9 lakh special repair of a link road), 1 no (drains, side
                    roads and a culvert in one work, which the "from ... to" exception let
                    through).
"""


QUEUE_BASELINE = {
    'NOID-338f02da': 'yes',
    'NOID-490f227a': 'yes',
    'NOID-4c60f54d': 'yes',
    'NOID-73ce0094': 'yes',
    'NOID-7eca39cf': 'grey',
    'NOID-9a1497ee': 'yes',
    'NOID-a0bb1c16': 'yes',
    'NOID-afb7d8db': 'yes',
    'NOID-b56e90f2': 'yes',
    'NOID-be37093b': 'yes',
    'NOID-d0b33267': 'yes',
    'NOID-fad403de': 'no',
    'NOID-fb99c117': 'yes',
    'WS/MP18004/2024-2025/151986': 'yes',
    'WS/MP18004/2024-2025/152096': 'yes',
    'WS/MP18004/2024-2025/152141': 'yes',
    'WS/MP18004/2024-2025/152143': 'yes',
    'WS/MP18004/2024-2025/152144': 'yes',
    'WS/MP18004/2024-2025/152145': 'yes',
    'WS/MP18004/2024-2025/152146': 'yes',
    'WS/MP18004/2024-2025/152147': 'yes',
    'WS/MP18004/2024-2025/156137': 'yes',
    'WS/MP18004/2024-2025/157507': 'yes',
    'WS/MP18004/2024-2025/157508': 'yes',
    'WS/MP18004/2024-2025/161321': 'yes',
    'WS/MP18184/2025-2026/161794': 'yes',
    'WS/MP18184/2025-2026/163648': 'yes',
    'WS/MP18252/2025-2026/173909': 'yes',
    'WS/MP18311/2024-2025/136624': 'yes',
    'WS/MP18357/2025-2026/225305': 'yes',
    'WS/MP18400/2025-2026/159569': 'yes',
    'WS/MP391/2025-2026/166886': 'yes',
    'WS/MP479/2025-2026/189423': 'yes',
    'WS/MP479/2025-2026/193017': 'yes',
    'WS/MP479/2025-2026/204328': 'yes',
    'WS/MP644/2024-2025/151113': 'yes',
    'WS/MP644/2024-2025/151191': 'yes',
    'WS/MP644/2024-2025/151374': 'yes',
    'WS/MP644/2024-2025/151376': 'yes',
    'WS/MP755/2025-2026/261328': 'yes',
}

R07 = {
    'NOID-2b027801': 'yes',
    'WS/MP18002/2026-2027/278233': 'grey',
    'WS/MP18048/2024-2025/149427': 'no',
    'WS/MP18069/2024-2025/163042': 'yes',
    'WS/MP18069/2025-2026/162525': 'grey',
    'WS/MP18346/2024-2025/162440': 'yes',
    'WS/MP18346/2024-2025/162482': 'yes',
    'WS/MP300/2024-2025/160004': 'yes',
    'WS/MP313/2024-2025/138663': 'yes',
    'WS/MP347/2024-2025/140240': 'no',
    'WS/MP352/2025-2026/156734': 'no',
    'WS/MP558/2025-2026/215865': 'yes',
}

SPLIT_AT_ONE_SITE = {
    'WS/MP18184/2025-2026/161840': 'no',
    'WS/MP18188/2025-2026/159687': 'grey',
    'WS/MP18227/2024-2025/148772': 'yes',
    'WS/MP18251/2024-2025/155504': 'grey',
    'WS/MP18252/2025-2026/157233': 'no',
    'WS/MP18278/2024-2025/135170': 'yes',
    'WS/MP18351/2024-2025/158088': 'yes',
    'WS/MP18380/2024-2025/144081': 'grey',
    'WS/MP444/2024-2025/146251': 'grey',
    'WS/MP479/2024-2025/140168': 'no',
    'WS/MP574/2025-2026/145482': 'yes',
    'WS/MP852/2024-2025/154562': 'yes',
}

REPEATED_WHILE_OPEN = {
    'WS/MP18006/2024-2025/136186': 'yes',
    'WS/MP18006/2024-2025/136189': 'grey',
    'WS/MP18006/2024-2025/150013': 'yes',
    'WS/MP479/2024-2025/138308': 'no',
    'WS/MP479/2024-2025/140165': 'no',
    'WS/MP479/2025-2026/160374': 'no',
    'WS/MP479/2025-2026/160381': 'no',
}

R14 = {
    'WS/MP18039/2025-2026/162175': 'yes',
    'WS/MP18114/2025-2026/157541': 'yes',
    'WS/MP18180/2025-2026/149577': 'yes',
    'WS/MP18183/2025-2026/140746': 'yes',
    'WS/MP18393/2025-2026/152027': 'yes',
    'WS/MP313/2024-2025/140980': 'yes',
    'WS/MP413/2025-2026/163345': 'yes',
    'WS/MP740/2025-2026/160526': 'yes',
    'WS/MP761/2024-2025/144933': 'yes',
    'WS/MP761/2024-2025/144962': 'yes',
    'WS/MP761/2025-2026/153927': 'yes',
    'WS/MP761/2025-2026/159654': 'yes',
}

QUEUE_V3 = {
    'NOID-7eca39cf': 'grey',
    'WS/MP017/2025-2026/160030': 'yes',
    'WS/MP017/2025-2026/161188': 'yes',
    'WS/MP017/2025-2026/202449': 'yes',
    'WS/MP18004/2024-2025/152141': 'yes',
    'WS/MP18009/2024-2025/163081': 'yes',
    'WS/MP18019/2024-2025/137608': 'yes',
    'WS/MP18039/2025-2026/201138': 'yes',
    'WS/MP18045/2024-2025/136999': 'yes',
    'WS/MP18108/2025-2026/195805': 'yes',
    'WS/MP18108/2025-2026/203466': 'yes',
    'WS/MP18108/2025-2026/203467': 'yes',
    'WS/MP18111/2025-2026/144098': 'yes',
    'WS/MP18111/2025-2026/144099': 'yes',
    'WS/MP18119/2025-2026/163575': 'yes',
    'WS/MP18124/2025-2026/162319': 'yes',
    'WS/MP18124/2025-2026/162344': 'yes',
    'WS/MP18124/2025-2026/162363': 'yes',
    'WS/MP18180/2025-2026/149582': 'yes',
    'WS/MP18180/2025-2026/149584': 'yes',
    'WS/MP18181/2025-2026/222364': 'no',
    'WS/MP18196/2025-2026/195856': 'yes',
    'WS/MP18227/2025-2026/174109': 'yes',
    'WS/MP18250/2026-2027/140437': 'no',
    'WS/MP18255/2025-2026/220178': 'yes',
    'WS/MP18263/2025-2026/149951': 'yes',
    'WS/MP18346/2024-2025/162489': 'yes',
    'WS/MP18346/2024-2025/162602': 'yes',
    'WS/MP18351/2024-2025/160019': 'yes',
    'WS/MP317/2024-2025/145198': 'yes',
    'WS/MP347/2024-2025/138112': 'yes',
    'WS/MP381/2025-2026/203177': 'yes',
    'WS/MP479/2025-2026/190885': 'yes',
    'WS/MP479/2025-2026/193007': 'yes',
    'WS/MP644/2024-2025/151376': 'yes',
    'WS/MP644/2024-2025/151387': 'yes',
    'WS/MP664/2025-2026/146335': 'yes',
    'WS/MP740/2025-2026/160532': 'yes',
    'WS/MP745/2025-2026/141430': 'yes',
    'WS/MP755/2024-2025/163142': 'yes',
}

# gained by the final reader: is the flag right?  dropped: was main's flag right?
R07_CHANGES = {
    'WS/MP18075/2025-2026/187350': ('gained', 'yes'),
    'WS/MP18080/2025-2026/181934': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219208': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219210': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219211': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219212': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219213': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219214': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219215': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219216': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219217': ('gained', 'yes'),
    'WS/MP18196/2025-2026/219218': ('gained', 'yes'),
    'WS/MP18227/2025-2026/174109': ('gained', 'yes'),
    'WS/MP381/2025-2026/203177': ('gained', 'yes'),
    'WS/MP417/2025-2026/253695': ('gained', 'yes'),
    'WS/MP18048/2024-2025/149427': ('dropped', 'no'),
    'WS/MP18181/2025-2026/222364': ('dropped', 'no'),
    'WS/MP18250/2026-2027/140437': ('dropped', 'no'),
    'WS/MP347/2024-2025/140240': ('dropped', 'no'),
    'WS/MP352/2025-2026/156734': ('dropped', 'no'),
    'WS/MP555/2025-2026/155818': ('dropped', 'grey'),
}

QUEUE_FINAL = {
    'WS/MP18004/2024-2025/152143': 'yes',
    'WS/MP18009/2024-2025/161192': 'yes',
    'WS/MP18009/2024-2025/163082': 'yes',
    'WS/MP18019/2024-2025/137608': 'yes',
    'WS/MP18036/2025-2026/205830': 'yes',
    'WS/MP18036/2025-2026/262926': 'yes',
    'WS/MP18037/2024-2025/177019': 'yes',
    'WS/MP18045/2024-2025/136999': 'yes',
    'WS/MP18045/2025-2026/198044': 'yes',
    'WS/MP18108/2025-2026/203466': 'grey',
    'WS/MP18111/2025-2026/144099': 'yes',
    'WS/MP18113/2025-2026/162518': 'yes',
    'WS/MP18123/2026-2027/242705': 'yes',
    'WS/MP18124/2025-2026/162323': 'yes',
    'WS/MP18124/2025-2026/162358': 'yes',
    'WS/MP18124/2025-2026/162368': 'yes',
    'WS/MP18180/2025-2026/149583': 'yes',
    'WS/MP18180/2025-2026/149585': 'yes',
    'WS/MP18184/2025-2026/210972': 'yes',
    'WS/MP18196/2025-2026/219215': 'yes',
    'WS/MP18196/2025-2026/244260': 'yes',
    'WS/MP18207/2025-2026/174861': 'yes',
    'WS/MP18207/2025-2026/174863': 'yes',
    'WS/MP18263/2025-2026/149952': 'yes',
    'WS/MP18346/2024-2025/162607': 'yes',
    'WS/MP18351/2024-2025/160020': 'yes',
    'WS/MP18393/2025-2026/140466': 'yes',
    'WS/MP317/2024-2025/145371': 'yes',
    'WS/MP347/2024-2025/138112': 'yes',
    'WS/MP549/2025-2026/214109': 'yes',
    'WS/MP640/2025-2026/158763': 'yes',
    'WS/MP644/2024-2025/151387': 'yes',
    'WS/MP644/2024-2025/151390': 'yes',
    'WS/MP664/2025-2026/146362': 'yes',
    'WS/MP672/2024-2025/144105': 'yes',
    'WS/MP740/2025-2026/160534': 'yes',
    'WS/MP747/2025-2026/141752': 'yes',
    'WS/MP755/2024-2025/163248': 'yes',
    'WS/MP755/2024-2025/163620': 'yes',
    'WS/MP827/2025-2026/214128': 'yes',
}

COST_SAMPLE = {
    'WS/MP18355/2025-2026/158366': 'no',
    'WS/MP859/2024-2025/152782': 'yes',
    'WS/MP18019/2024-2025/137730': 'grey',
    'WS/MP18110/2025-2026/209772': 'grey',
    'WS/MP459/2025-2026/149088': 'no',
    'WS/MP18069/2025-2026/162985': 'grey',
    'WS/MP18203/2024-2025/154497': 'yes',
    'WS/MP18328/2024-2025/144156': 'no',
    'WS/MP18014/2025-2026/218029': 'grey',
    'WS/MP18232/2024-2025/139498': 'no',
    'WS/MP577/2025-2026/146153': 'grey',
    'WS/MP644/2024-2025/151113': 'yes',
}

# dropped: was the old flag a real price question?  gained: is the new flag one?
COST_CHANGES = {
    'NOID-a0bb1c16': ('dropped', 'no'),
    'WS/MP18004/2024-2025/161319': ('dropped', 'no'),
    'WS/MP18004/2024-2025/161321': ('dropped', 'no'),
    'WS/MP18198/2025-2026/193991': ('dropped', 'no'),
    'WS/MP18355/2025-2026/158366': ('dropped', 'no'),
    'WS/MP18393/2024-2025/163262': ('dropped', 'no'),
    'WS/MP459/2025-2026/149088': ('dropped', 'no'),
    'WS/MP18155/2024-2025/177940': ('gained', 'grey'),
    'WS/MP337/2025-2026/160005': ('gained', 'no'),
}
