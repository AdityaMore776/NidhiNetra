"""R06 (recorded complete before it was recommended) read by eye on the hosted data, T056.

Source: `data/trial/r06_rows.py` run by the owner on the hosted database, 2 Oct 2026 (counts in
results/r06_hosted.json; the cases were printed masked and are not stored). Of 2,09,993 works,
85,773 have both dates and 1,105 are recorded complete 7+ days before their recommendation.
R06's own check rates 21 of them MEDIUM ("stands out": not a bulk-entry quarter, not an office's
habit) and 1,084 LOW (678 office habit, 285 bulk-entry quarter, 121 less distinct).

R06_MEDIUM   10 of the 21 MEDIUM cases, the first 10 in the script's fixed random order (md5 of
             the work id), read 2 Oct 2026: 10 yes. Constructions and lights of Rs 2.99-37.87
             lakh (7 roads, a hall, a hospital toilet block, a high-mast light) recorded
             complete 15-137 days before the MP's recommendation, none with a sanction date on
             the record. On the standard used for R13 and R14 (the dates need checking in every
             case) each is worth an officer's look: either a date is wrong or the work was
             funded after it was built. Caveat: 8 of the 10 are district offices in Kerala, so a state-wide
             recording practice is possible; if more reads show it, the state's cases become a
             records note like bulk entry.
R06_LOW      10 LOW cases from the same run, for the record only (NOT counted): 7 office habit,
             2 bulk-entry quarter, 1 less distinct. By design these are records notes about the
             office (listed once), not findings about the work, so they were not judged as
             findings; R06_NOTE_RISK keeps their weight where it was (agents/compliance/agent.py).

Privacy: two of the printed descriptions name private people (house and land owners) that the
masker (validation/pii.py) does not catch ("<name> house", "<name> land"). Only work ids are kept
here.
"""

R06_MEDIUM = {
    'WS/MP350/2024-2025/178309': 'yes',
    'WS/MP347/2024-2025/140240': 'yes',
    'WS/MP096/2024-2025/182031': 'yes',
    'WS/MP101/2024-2025/153062': 'yes',
    'WS/MP162/2024-2025/176337': 'yes',
    'WS/MP099/2024-2025/133001': 'yes',
    'WS/MP112/2024-2025/136783': 'yes',
    'WS/MP842/2024-2025/175817': 'yes',
    'WS/MP096/2024-2025/132961': 'yes',
    'WS/MP096/2024-2025/145604': 'yes',
}

R06_LOW = {
    'WS/MP735/2023-2024/60664': 'office habit',
    'WS/MP346/2023-2024/66912': 'office habit',
    'WS/MP720/2024-2025/124448': 'office habit',
    'WS/MP346/2023-2024/72849': 'office habit',
    'WS/MP326/2023-2024/23411': 'bulk-entry quarter',
    'WS/MP310/2023-2024/12784': 'office habit',
    'WS/MP166/2024-2025/126272': 'office habit',
    'WS/MP678/2023-2024/37188': 'less distinct',
    'WS/MP687/2024-2025/110330': 'bulk-entry quarter',
    'WS/MP346/2023-2024/72858': 'office habit',
}

if __name__ == "__main__":
    yes = sum(v == "yes" for v in R06_MEDIUM.values())
    print(f"R06 MEDIUM read: {yes} yes of {len(R06_MEDIUM)}; LOW sample (not counted): "
          f"{len(R06_LOW)}")
