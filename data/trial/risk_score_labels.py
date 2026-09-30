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
