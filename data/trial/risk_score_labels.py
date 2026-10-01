"""By-eye labels for the risk score's review queue (T050), 30 Sept 2026.

30 random works from the queue (CRITICAL + HIGH), seed 50, drawn after the cut-offs froze
(results/risk_score_queue_sample.csv, written by data/dry_run.py). Each was read with its
description and the score's reasons:
  "worth_checking"  at least one reason is a real question an officer should look into
  "explained"       the reasons fall away on reading: village-level entries ("solar light in
                    village X" twice is two lights), a list of many locations read as one
                    price, "GP and other villages"
Two earlier random samples (seeds 7 and 99) were read while setting the cut-offs and the
series rule, so they are not counted here.
"""

QUEUE = {
    'NOREF-df641823ae2635': 'worth_checking',
    'WS/MP636/2024-2025/18927': 'explained',
    'NOREF-ca449953afc406': 'worth_checking',
    'NOREF-b7c5b07c3f10e6': 'worth_checking',
    'NOREF-010fba1579575c': 'worth_checking',
    'NOREF-b14cbede407a6e': 'worth_checking',
    'WS/MP521/2023-2024/3102': 'worth_checking',
    'NOREF-32770d67c103fc': 'worth_checking',
    'WS/MP772/2024-2025/63378': 'worth_checking',
    'WS/MP371/2023-2024/35524': 'worth_checking',
    'WS/MP18319/2024-2025/158795': 'worth_checking',
    'WS/MP084/2024-2025/134113': 'worth_checking',
    'WS/MP084/2024-2025/133937': 'worth_checking',
    'WS/MP565/2023-2024/15917': 'worth_checking',
    'WS/MP084/2024-2025/133938': 'worth_checking',
    'WS/MP18120/2025-2026/193720': 'worth_checking',
    'NOREF-21cf0a4907e460': 'worth_checking',
    'WS/MP771/2023-2024/56525': 'worth_checking',
    'NOREF-36fc42a8ff3680': 'worth_checking',
    'NOREF-7613cdcb919c46': 'worth_checking',
    'WS/MP781/2023-2024/53396': 'explained',
    'WS/MP434/2023-2024/19037': 'worth_checking',
    'WS/MP781/2023-2024/52776': 'explained',
    'WS/MP498/2024-2025/63202': 'worth_checking',
    'WS/MP300/2023-2024/390': 'explained',
    'WS/MP476/2024-2025/78326': 'worth_checking',
    'WS/MP781/2023-2024/54256': 'explained',
    'WS/MP476/2024-2025/68853': 'worth_checking',
    'WS/MP781/2023-2024/54266': 'explained',
    'NOREF-14c35fc47e999e': 'worth_checking',
}

# T051 (1 Oct 2026): 30 random works from the NEW queue (HIGH >= 0.22, CRITICAL >= 0.30), seed 51,
# none of them in QUEUE above (results/risk_score_queue_sample_t051.csv). Same meaning of
# "worth_checking" as above: 30/30. STRICT = a reason OTHER than a sanction or completion
# delay survives reading: 27/30 (the 3 "delay_only": a duplicate that is a different job at
# one spot, generic hearing-aid purchases, a shed vs a road at one gaushala).
QUEUE_T051 = {
    'NOREF-9f3ce477e89045': "worth_checking",
    'NOREF-042964e8bbd425': "worth_checking",
    'WS/MP450/2025-2026/173349': "worth_checking",
    'NOREF-a64b4a3399077c': "worth_checking",
    'WS/MP300/2023-2024/240': "worth_checking",
    'WS/MP439/2025-2026/169448': "worth_checking",
    'NOREF-91cc1d920e7798': "worth_checking",
    'WS/MP450/2025-2026/173534': "worth_checking",
    'NOREF-9212163fc8d1ca': "delay_only",
    'NOREF-51edd6be4aec4e': "worth_checking",
    'WS/MP593/2023-2024/9217': "worth_checking",
    'WS/MP761/2024-2025/150990': "worth_checking",
    'NOREF-895875ffddbb35': "worth_checking",
    'NOREF-b21ca30e067333': "delay_only",
    'WS/MP623/2024-2025/55273': "worth_checking",
    'NOREF-50d94f69c1c6bf': "worth_checking",
    'NOREF-052d6dce205ab7': "worth_checking",
    'NOREF-1ef54530e865c0': "delay_only",
    'NOREF-5de215376de56b': "worth_checking",
    'NOREF-9b8cc1c83f856a': "worth_checking",
    'NOREF-2b91aefd3ae72b': "worth_checking",
    'NOREF-59067acbf2b148': "worth_checking",
    'NOREF-99377a3216122e': "worth_checking",
    'NOREF-1c4082abe9c74e': "worth_checking",
    'WS/MP18388/2025-2026/184093': "worth_checking",
    'NOREF-f445c6f23519ad': "worth_checking",
    'NOREF-3f1c4fe4982321': "worth_checking",
    'NOREF-d0cb9ef89b223c': "worth_checking",
    'NOREF-51e939664e824d': "worth_checking",
    'NOREF-2f57d7228d9395': "worth_checking",
}
