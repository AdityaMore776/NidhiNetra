r"""The generic-word list the Duplicate & Split engine uses to tell place names from ordinary words (T051).

A description names WHAT is built ("construction of CC road") and WHERE ("at Sitapur, ward 4").
Two works can only be the same site when their place words agree, so the engine needs to know which
words are places. Counting how rare a word is in today's corpus (the T030 rule, df <= 60) ties the
engine to this one file: a new village is unknown, and the count changes every time the data grows.

So the rule is fixed in advance and the result is stored as reference data:

  a word is GENERIC when it appears in at least 5% of districts (38 of 746 in the 2026 export):
  words used everywhere describe works, not places ("construction", "road", "interlocking",
  "nagar", and very common village names like "rampur" that cannot pin down one site anyway)
  plus the hand-written list of work words kept from T030 (Hindi words like "khadanja",
  "nirman", "sadak" that are generic but regional).

Any word NOT in the list is a place word, including names the engine has never seen.

Writes apps/engine/drishti/reference/generic_words.txt (one word per line, sorted).
Run: apps\engine\.venv\Scripts\python.exe data\build_generic_words.py
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "engine" / "drishti" / "reference" / "generic_words.txt"
SPREAD = 0.05
WORD = re.compile(r"[a-z]{4,}")
# Work words kept from data/build_dup_split.py (T030): generic, but some are regional.
STOP = set("""construction installation providing supply work works road roads village near from
with under ward block district gram panchayat colony hall community school building drain drains
street light lights solar high mast cement concrete toilet public open repair renovation boundary
wall water tank borewell hand pump shed shelter the and for into interlocking karya nirman sadak
khadanja marg bhawan kaksha purchase books library installation center centre main house kharanja
khadanza nali naali sadk sarak pakka pakki nirmaan""".split())

# Read by eye on the eSAKSHI dashboard tables (2 Oct 2026): words the engine took for places
# because they are rare in one district, though they are ordinary English, spec-sheet, Hindi or
# regional work words, abbreviations of offices, or common typos. Drawn from candidate words
# found in 3+ states (a village name rarely is); every word that could be a person's or a
# place's name was left out. Without them "Two Piece", "Manual Ladder ... Lithium" and
# "Nadaga Medai" (a stage) made identical works of different sites read as "one place".
EXTRA_2026 = set("""following grill monitor nearby software tricycle tricycles hardware hearing
purifier related wire wiring wireless artificial clinic company dispensary flat interactive life
lock metre metres mile mortuary poll special wood wooden above circuit clean collection delivery
entry fixtures grid integrated items levelling leveling limb major meal newly nursing plantation
plus replacement scooter sewerage sewage support vegetable western eastern northern southern
abled auto built build bungalow bunglow chamber convent covering dated dealer dental disabled
disabilities display executing executed executive filter footbridge golden hamlet inch inches
labour last like little local make making male female mall metal mount mounted octagonal only
piece pitch portion radio range recommended recommendation reconstruction rice roofing seater
settlement size study surface surrounding traders transport transportation warranty washing
widening wife wing about adjoining ahead anti apparatus approximately approx army asphalt
attachment avenue barrier based bath before below bike cable cattle ceiling chain challenged
cinema citizens citizen classes cochlear collectorate commissioning conference connect cutting
dark daughter details distance dome down dumping earthen eight enclosure energy enhance expansion
fabricated farmers farmer financial fishery former freezer friends game gravelling guardwall have
having hockey improve incomplete jurisdiction jungle kabaddi laptop learning litre litres ltrs
long manual mass mate mineral minimast minor monitoring museum must need niche operated outdoor
overhead passage patient patients physically private property prosthesis pull pumping railing
research revenue roadside royal sanitation sound strengthening sugar supplying tech testing
theater theatre these township turn voltage volt warehouse weavers weekly without workers
workshed zero ladder module ferro lithium battery batteries panel panels pole poles watt watts
specifications standard super quality proper full free spot view white waste windows visual
vending stretcher swings synthetic trolley screen scanner speaker studio counter canteen bakery
grocery stall emergency elementary engineering engineer environment equipped erosion feeder
fitted generator heater heritage industrial information institution institutions interior
international knowledge large leader living load marble martyr mats mother pavilion pedestrian
pickup plaster pressure processor producers reservoir retrofitting rubber running seated segment
self septic setup storm stream surveillance teacher teachers teaching treatment tribe upgrading
using valley veranda varanda workers zero
abadi avam tahsil karyalay karyalaya vibhag vibhinn sankhya sameep samip sthapna sthapana sudhar
lagbhag sath andar bich sabji mitti dwar dwara diwar diwari pustakalay pustkalaya vachnalay
shauchalay sichai vidyut vidhut vidyutikaran upkaran yojna nirmit kray lagane karne chhota chota
chhoti choti chhote bade nava nayi nawa uncha uchch uchcha ucch swasthya sabhagar rangmanch vyayam
udhyan bagicha bagan akhada akhara shamshanghat kabarsthan kabristan eidgah mazar majar samadhi
goshala thakurbari imambada karbala mouza mauza mauja khasra bigha medai nadaga veedhi katta
ohsr gsss ghss drda ongc bsnl pacs zphs icds gruh bhandar sthan dono jala kuan kuwa kund
nstallation onstruction schhol hosue tample transfarmar pamp graund graval
aanganwadi aapurti adhishtapan adhishthapan adhishthapit adhisthapan adhisthapit aganwadi
anganbadi anganwari apurti baratghar chaharadiwari chahardiwari chardiwari chaudikaran ghaat
intarlocking jaal jalnikasi jeernoddhar jirnoddhar jirnodhar kabrastan khareed kharid lagana
mahavidyalay maramat marammat mrammat naala nikasi peyjal pokhara prakhand pratiksha pustak
pustakalaya sabhamandap samuhik saundarikaran saundaryikaran shauchalaya shmashan snanagar
sondaryikaran soundaryikaran sthapit sundarikaran tinshed vachanalaya vishram vishramalay
vistarikaran vitaran""".split())


def main() -> None:
    w = pd.read_parquet(ROOT / "data" / "build" / "works.parquet")
    w = w[w.description.notna()]
    n_districts = w.district_lgd.nunique()
    seen: dict[str, set] = defaultdict(set)
    for d, t in zip(w.district_lgd.astype(str), w.description.str.lower(), strict=True):
        for x in set(WORD.findall(t)):
            seen[x].add(d)
    generic = {x for x, ds in seen.items() if len(ds) >= SPREAD * n_districts} | {
        x for x in STOP | EXTRA_2026 if len(x) >= 4}
    OUT.write_text("# Generated by data/build_generic_words.py: words found in at least "
                   f"{SPREAD:.0%} of {n_districts} districts, plus T030's work words and the "
                   "2026 dashboard read (EXTRA_2026).\n"
                   + "\n".join(sorted(generic)) + "\n", encoding="utf-8")
    print(f"{len(generic):,} generic words ({n_districts} districts) -> {OUT}")


if __name__ == "__main__":
    main()
