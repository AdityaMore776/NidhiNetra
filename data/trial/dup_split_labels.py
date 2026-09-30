"""By-eye labels for the duplicate pairs (data/build_dup_split.py), 30 Sept 2026.

Each pair (work a, work b) was read in full and labelled:
  "same"       reads as the same work recorded twice: same job, same site; worth checking
  "different"  different sites (other village, survey/property number, stretch, house),
               a staged continuation, or generic text that names no site to compare

DEV    the top 50 by score after the number and series rules (results/dup_split_pairs_dev.csv);
       the first reading of an earlier top 50 (25/50) led to those two rules.
TEST1  40 random flagged pairs outside the top 50, drawn after the rules froze
       (results/dup_split_pairs_test1.csv, seed 41). Its reading found the subset-match fault
       (a panchayat name shared by two villages) and led to the place rule change, so the
       next fresh sample is TEST2.
TEST2  40 random flagged pairs outside the top 50, none read before, drawn after the place
       rule froze (results/dup_split_pairs_test2.csv, seed 42). Reported whatever it shows.
GROUPS_TEST  30 random groups (results/dup_split_groups_test.csv, seed 26), drawn after the
       group rules froze (two earlier samples, seeds 5 and 11, were read to fix them):
         "split"      same_site_split that reads as one job at one site in pieces / twice
         "explained"  same_site_split that is not (different spots, sides, several sites)
         "series"     bulk_order correctly read as one purchase filed as many works
"""

DEV = {
    ('NOREF-2a651379979fd3', 'NOREF-e39d5880f092e0'): 'same',
    ('WS/MP662/2025-2026/165325', 'WS/MP662/2024-2025/130595'): 'same',
    ('WS/MP630/2023-2024/70393', 'WS/MP630/2024-2025/109430'): 'same',
    ('WS/MP572/2023-2024/44567', 'WS/MP572/2025-2026/77456'): 'same',
    ('NOREF-8f3c4eaeb68a21', 'WS/MP18089/2026-2027/233381'): 'same',
    ('WS/MP880/2025-2026/188903', 'NOREF-309befcb85bbd9'): 'same',
    ('WS/MP021/2025-2026/225744', 'WS/MP021/2025-2026/242831'): 'different',
    ('WS/MP593/2023-2024/9217', 'WS/MP593/2023-2024/43713'): 'same',
    ('WS/MP18403/2026-2027/271871', 'NOREF-b013d3d1505580'): 'same',
    ('WS/MP623/2024-2025/55273', 'NOREF-3cf491a8b668dd'): 'same',
    ('WS/MP761/2024-2025/164716', 'NOREF-b6ad392c3942cd'): 'different',
    ('WS/MP623/2024-2025/52826', 'WS/MP623/2024-2025/107752'): 'same',
    ('NOREF-89951977b00c0c', 'WS/MP18030/2025-2026/213612'): 'same',
    ('NOREF-a08b7f0ad01586', 'NOREF-4b2ec41295da5b'): 'same',
    ('WS/MP761/2024-2025/150990', 'NOREF-7f69ff5e816ec7'): 'same',
    ('WS/MP613/2024-2025/19358', 'NOREF-141b291caef845'): 'different',
    ('WS/MP18155/2025-2026/243422', 'WS/MP18155/2025-2026/260963'): 'different',
    ('WS/MP338/2024-2025/41881', 'WS/MP338/2024-2025/84934'): 'same',
    ('WS/MP630/2026-2027/66635', 'NOREF-a7fbff60afcb9c'): 'same',
    ('WS/MP758/2025-2026/170881', 'WS/MP758/2025-2026/201225'): 'same',
    ('WS/MP18040/2024-2025/157358', 'WS/MP18040/2025-2026/184184'): 'same',
    ('WS/MP18113/2025-2026/192641', 'WS/MP18113/2025-2026/219666'): 'same',
    ('WS/MP738/2023-2024/50325', 'WS/MP738/2024-2025/131993'): 'different',
    ('WS/MP416/2024-2025/169649', 'WS/MP544/2025-2026/176646'): 'different',
    ('WS/MP662/2024-2025/165322', 'WS/MP662/2024-2025/130548'): 'different',
    ('WS/MP371/2023-2024/48704', 'WS/MP371/2023-2024/102946'): 'different',
    ('NOREF-a8106e40e2756a', 'NOREF-0dfc169aa9ab1b'): 'different',
    ('WS/MP705/2023-2024/31334', 'WS/MP705/2023-2024/69233'): 'different',
    ('NOREF-0eb4fb258763f9', 'WS/MP767/2023-2024/66584'): 'different',
    ('WS/MP613/2023-2024/19201', 'WS/MP613/2023-2024/79784'): 'same',
    ('WS/MP641/2024-2025/153873', 'WS/MP641/2025-2026/179569'): 'same',
    ('WS/MP163/2024-2025/136103', 'WS/MP162/2024-2025/141932'): 'same',
    ('WS/MP561/2025-2026/211209', 'WS/MP561/2025-2026/234301'): 'same',
    ('NOREF-81a50b194f42ea', 'NOREF-51bdc923e2686d'): 'same',
    ('WS/MP18031/2025-2026/239362', 'NOREF-1817a713a8870c'): 'same',
    ('WS/MP793/2024-2025/165157', 'WS/MP182/2024-2025/165852'): 'different',
    ('NOREF-c747bcfc3b3850', 'NOREF-2d4a6709555f9c'): 'different',
    ('NOREF-3a3a5096c8d4d9', 'NOREF-9d15ff6a21328a'): 'different',
    ('WS/MP18178/2024-2025/174396', 'WS/MP18178/2025-2026/202124'): 'different',
    ('WS/MP385/2024-2025/66364', 'WS/MP385/2024-2025/114130'): 'different',
    ('WS/MP421/2023-2024/8423', 'WS/MP421/2023-2024/52368'): 'different',
    ('WS/MP630/2024-2025/70247', 'WS/MP630/2024-2025/109430'): 'same',
    ('WS/MP026/2025-2026/200363', 'WS/MP026/2025-2026/222306'): 'same',
    ('NOREF-81a50b194f42ea', 'NOREF-02843f79befe4c'): 'same',
    ('NOREF-81a50b194f42ea', 'NOREF-ce525574eeb73d'): 'different',
    ('NOREF-32770d67c103fc', 'NOREF-7098741f176ee5'): 'different',
    ('WS/MP421/2023-2024/8424', 'WS/MP421/2023-2024/52366'): 'same',
    ('WS/MP433/2023-2024/10481', 'WS/MP433/2023-2024/52679'): 'different',
    ('WS/MP630/2025-2026/70759', 'NOREF-2904eb883fd344'): 'same',
    ('WS/MP552/2024-2025/169392', 'WS/MP552/2025-2026/194127'): 'different',
}

TEST1 = {
    ('WS/MP883/2023-2024/74952', 'WS/MP883/2025-2026/154968'): 'different',
    ('NOREF-fd401da8334f97', 'NOREF-c7d717737d8b6d'): 'same',
    ('WS/MP18385/2025-2026/247011', 'WS/MP18385/2025-2026/261459'): 'different',
    ('WS/MP086/2025-2026/227467', 'WS/MP086/2025-2026/255726'): 'different',
    ('WS/MP568/2025-2026/184560', 'WS/MP568/2025-2026/225209'): 'different',
    ('WS/MP086/2025-2026/174496', 'NOREF-021467a74645dd'): 'different',
    ('WS/MP478/2025-2026/180991', 'NOREF-0ea95e65b5fe49'): 'same',
    ('WS/MP416/2023-2024/7404', 'WS/MP416/2023-2024/37737'): 'different',
    ('WS/MP582/2023-2024/89055', 'WS/MP582/2025-2026/239527'): 'different',
    ('WS/MP743/2023-2024/57647', 'WS/MP743/2024-2025/143067'): 'different',
    ('WS/MP889/2024-2025/147869', 'WS/MP889/2024-2025/162276'): 'different',
    ('WS/MP18190/2025-2026/171382', 'WS/MP18190/2025-2026/239218'): 'different',
    ('WS/MP18236/2024-2025/139093', 'WS/MP18236/2025-2026/177475'): 'different',
    ('WS/MP18186/2025-2026/167718', 'NOREF-9214ccc6be0ee2'): 'same',
    ('WS/MP781/2023-2024/61740', 'WS/MP781/2024-2025/130570'): 'different',
    ('WS/MP579/2024-2025/105358', 'WS/MP579/2025-2026/197145'): 'different',
    ('NOREF-e1ba7fd8d76222', 'NOREF-14951947e54779'): 'same',
    ('WS/MP18214/2024-2025/153406', 'WS/MP18214/2026-2027/262797'): 'different',
    ('WS/MP544/2023-2024/116749', 'WS/MP544/2025-2026/176646'): 'different',
    ('WS/MP892/2025-2026/211631', 'WS/MP892/2025-2026/252321'): 'different',
    ('WS/MP041/2025-2026/270927', 'NOREF-f7e589669ab280'): 'different',
    ('WS/MP582/2024-2025/137326', 'WS/MP582/2025-2026/215536'): 'different',
    ('WS/MP18214/2024-2025/153393', 'NOREF-8978bca0956147'): 'different',
    ('NOREF-65bc7d62ddb660', 'NOREF-9007d3e7ac0e90'): 'different',
    ('WS/MP18155/2025-2026/210642', 'WS/MP18155/2025-2026/245571'): 'different',
    ('WS/MP18231/2025-2026/224254', 'NOREF-6821a8f105a95e'): 'different',
    ('WS/MP371/2023-2024/64932', 'WS/MP18358/2024-2025/164805'): 'same',
    ('WS/MP524/2023-2024/85803', 'WS/MP18334/2024-2025/137937'): 'different',
    ('WS/MP582/2024-2025/137332', 'WS/MP582/2025-2026/205793'): 'different',
    ('NOREF-776e3d96efa109', 'NOREF-e70f8e3839639a'): 'different',
    ('WS/MP18322/2025-2026/183079', 'NOREF-517e2e64f6f322'): 'different',
    ('WS/MP394/2025-2026/170086', 'NOREF-16cd13e6f716d3'): 'different',
    ('WS/MP232/2026-2027/203084', 'NOREF-ee84c0e38ec5fb'): 'same',
    ('WS/MP435/2023-2024/89147', 'WS/MP435/2025-2026/218303'): 'different',
    ('WS/MP753/2025-2026/237917', 'WS/MP753/2024-2025/57933'): 'same',
    ('WS/MP18228/2024-2025/147124', 'WS/MP18228/2025-2026/182529'): 'different',
    ('WS/MP18157/2024-2025/163170', 'NOREF-0ba7d98374c662'): 'different',
    ('WS/MP450/2025-2026/173526', 'WS/MP450/2025-2026/173138'): 'different',
    ('WS/MP106/2025-2026/206952', 'NOREF-4101e197ab7ec1'): 'different',
    ('WS/MP435/2023-2024/85817', 'WS/MP435/2025-2026/218320'): 'different',
}

TEST2 = {
    ('NOREF-f8f904570873a1', 'WS/MP630/2024-2025/109430'): 'same',
    ('WS/MP18155/2024-2025/141709', 'WS/MP18155/2025-2026/198948'): 'different',
    ('WS/MP382/2023-2024/47207', 'WS/MP382/2023-2024/126164'): 'different',
    ('WS/MP18158/2025-2026/192812', 'WS/MP18158/2025-2026/221590'): 'same',
    ('WS/MP743/2024-2025/60371', 'WS/MP743/2025-2026/191347'): 'same',
    ('WS/MP805/2023-2024/47638', 'WS/MP805/2023-2024/114222'): 'same',
    ('WS/MP705/2023-2024/37965', 'WS/MP705/2023-2024/99280'): 'different',
    ('WS/MP574/2023-2024/115515', 'WS/MP574/2025-2026/212548'): 'same',
    ('WS/MP18051/2025-2026/195249', 'WS/MP18051/2025-2026/238739'): 'different',
    ('WS/MP840/2025-2026/206216', 'WS/MP840/2025-2026/244693'): 'different',
    ('WS/MP18043/2025-2026/198315', 'WS/MP18043/2025-2026/233567'): 'different',
    ('WS/MP18370/2025-2026/182556', 'WS/MP18370/2025-2026/254613'): 'same',
    ('WS/MP18222/2025-2026/170053', 'WS/MP18222/2025-2026/212782'): 'different',
    ('WS/MP371/2023-2024/64936', 'WS/MP18358/2025-2026/187861'): 'different',
    ('WS/MP618/2025-2026/171167', 'NOREF-77fca1f7abd47d'): 'same',
    ('WS/MP650/2024-2025/184591', 'WS/MP650/2025-2026/206644'): 'different',
    ('WS/MP18227/2025-2026/205702', 'WS/MP18227/2025-2026/224526'): 'same',
    ('WS/MP662/2025-2026/165324', 'WS/MP662/2024-2025/130602'): 'same',
    ('WS/MP015/2024-2025/134049', 'WS/MP163/2025-2026/203249'): 'different',
    ('WS/\t MP005/2025-2026/175481', 'WS/\t MP005/2025-2026/204115'): 'different',
    ('NOREF-0029b5a862e827', 'WS/MP18089/2025-2026/233384'): 'different',
    ('WS/MP18043/2025-2026/198319', 'WS/MP18043/2025-2026/233567'): 'different',
    ('WS/MP716/2023-2024/116439', 'WS/MP716/2025-2026/226681'): 'different',
    ('WS/MP623/2025-2026/54598', 'NOREF-c204d45626f884'): 'different',
    ('WS/MP623/2025-2026/53438', 'WS/MP623/2024-2025/107752'): 'same',
    ('NOREF-8e0b9b980ccf29', 'WS/MP450/2025-2026/173313'): 'different',
    ('WS/MP18011/2024-2025/173504', 'WS/MP18011/2025-2026/210241'): 'different',
    ('WS/MP479/2024-2025/138308', 'WS/MP479/2025-2026/160381'): 'different',
    ('NOREF-276fa00c42b83d', 'WS/MP090/2024-2025/134312'): 'same',
    ('WS/MP351/2025-2026/243018', 'NOREF-8c368f87eef8d6'): 'different',
    ('WS/MP070/2024-2025/133157', 'WS/MP070/2026-2027/279592'): 'different',
    ('WS/MP081/2024-2025/133866', 'WS/MP081/2025-2026/221260'): 'different',
    ('WS/MP18393/2025-2026/169151', 'WS/EXLS005/2025-2026/229743'): 'different',
    ('WS/MP867/2025-2026/241805', 'WS/MP867/2025-2026/255119'): 'same',
    ('WS/MP18338/2024-2025/149947', 'WS/MP18338/2025-2026/207138'): 'different',
    ('WS/MP630/2024-2025/69988', 'NOREF-30d7a4520e8480'): 'different',
    ('WS/MP444/2025-2026/200253', 'NOREF-d8d3ff7968fab2'): 'different',
    ('WS/MP18241/2025-2026/197044', 'NOREF-4211700e77ffbf'): 'same',
    ('WS/MP18283/2025-2026/258432', 'NOREF-e1128cf12a7963'): 'same',
    ('WS/MP607/2025-2026/233373', 'NOREF-e78da718be2548'): 'same',
}

GROUPS_TEST = {
    'G02439': 'split',   # same_site_split
    'G03034': 'split',   # same_site_split
    'G01360': 'split',   # same_site_split
    'G02098': 'series',   # bulk_order
    'G00973': 'series',   # bulk_order
    'G00541': 'split',   # same_site_split
    'G01158': 'series',   # bulk_order
    'G01157': 'series',   # bulk_order
    'G00882': 'series',   # bulk_order
    'G02633': 'split',   # same_site_split
    'G01398': 'split',   # same_site_split
    'G02065': 'series',   # bulk_order
    'G00709': 'series',   # bulk_order
    'G00994': 'series',   # bulk_order
    'G01633': 'explained',   # same_site_split
    'G00511': 'split',   # same_site_split
    'G00733': 'series',   # bulk_order
    'G00074': 'series',   # bulk_order
    'G00480': 'series',   # bulk_order
    'G00065': 'series',   # bulk_order
    'G01619': 'explained',   # same_site_split
    'G01505': 'explained',   # same_site_split
    'G02363': 'explained',   # same_site_split
    'G01827': 'split',   # same_site_split
    'G01326': 'series',   # bulk_order
    'G02922': 'series',   # bulk_order
    'G01030': 'explained',   # same_site_split
    'G02959': 'split',   # same_site_split
    'G00865': 'series',   # bulk_order
    'G01299': 'split',   # same_site_split
}
