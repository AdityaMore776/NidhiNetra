"""The Hindsight Claim Ladder dataset for a vision-language model (plan T150 §6; tasks T153, T155).

One item = (photo A from the last visit, photo B from this visit, the work type, the agency's claim)
-> the answer the model must give:

    {"same_place": "yes|no|unsure", "stage_A": <stage>, "stage_B": <stage>,
     "permanent_change": "yes|no|cant_tell", "verdict": "shown|not_shown|cant_tell",
     "reason": "<at most 25 words>"}

Where the answers come from (never from how busy a photo looks):
- GeoMGNREGA assets (geomgnrega.py): the portal's own stage photos, before (1), during (2), after
  (3).
  On the coarse ladder not started -> under way -> complete, stage 1 is "not started" and stage 3 is
  "complete". Stage 2 is only "at least under way" (many "during" photos already look finished), so
  no item ever asks whether stage 2 is complete.
- The claim ladder (C13) turns each pair into several claims with exact labels: a claim the later
  photo's stage covers is shown; a claim ahead of it is not shown; "done this period" for work that
  was
  already there in A is not shown (the same work claimed twice).
- Real "no progress" pairs: the two photos of one moment (before: view; during, often with workers:
  busy), the two after photos (double claim), the photos in reverse order (swapped), and a clearly
  different place (other site: can't tell).

The owner's rules (7 Oct 2026), enforced here:
1. "Progress" items only where progress is CERTAIN: a structural work (structural()) whose before ->
   after photos differ more than its own same-moment photos and by at least change.FLOOR
   (change.py).
2. Test and calibration assets get ONLY real, unedited photos: no edited image can reach a headline
   number. Every item says whether it is real (`real`) and how it was edited (`edits`).
3. Edited items (people pasted in, light changed, darkened, blocked) only for training, and every
   edit
   goes into BOTH answers (pasted people and new light also go into real progress pairs labelled
   shown), so an edit never gives the answer away. Their share is capped when curating, and they
   stay
   only if switching them off makes the model worse on the real test set (T154 ablation).
4. No drawn or rendered synthetic scenes (T146's synth.py) are used here at all.

Splits are by DISTRICT: every item of a district is in one split; the test districts are never seen
in
training (plan T150 §4.2). Photos stay on D:; only this code and counts enter git.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

LADDER = ("not started", "work under way", "complete")
STAGE_OF_PHOTO = {1: 0, 2: 1, 3: 2}          # portal stage -> ladder rung (2 = at least under way)
VERDICTS = ("shown", "not_shown", "cant_tell")
TRICKS = ("none", "view", "busy", "double_claim", "swapped", "other_site", "staged", "light",
          "dark", "occluded")
NO_PROGRESS_TRICKS = ("view", "busy", "double_claim", "swapped", "staged", "light")
EDIT_TRICKS = ("staged", "light", "dark", "occluded")         # made by editing pixels

SYSTEM = ("You check site photos of an Indian public work against the implementing agency's "
          "claim. Photo A is from the last visit and photo B from this visit, at the same spot. "
          "Judge only what is visible. Workers, vehicles, animals, stacked materials, light and "
          "shadows are not progress; only permanent structure added counts. Say cant_tell when "
          "the photos cannot decide (different place, too dark, view blocked). Never accuse "
          "anyone.")

# what a rung looks like, per work type (used in claims and reasons)
LOOKS: dict[str, tuple[str, str, str]] = {
    "road": ("an unpaved earth track", "road work under way", "a finished paved road"),
    "building": ("an open plot with no building", "a building under construction",
                 "a finished building"),
    "drain": ("open ground with no drain", "drain work under way", "a finished drain"),
    "boundary_wall": ("open ground with no wall", "a wall being built", "a finished wall"),
    "other": ("the site before work", "work under way", "the finished work"),
}

# claim wording: (english, hinglish, hindi) for "complete" and "under way"; {thing} = what is built
CLAIM_DONE = ("{thing} completed", "{thing} ka karya poorn", "{thing} का कार्य पूर्ण")
CLAIM_STARTED = ("{thing}: work started and under way", "{thing} ka karya chalu hai",
                 "{thing} का कार्य प्रगति पर")
CLAIM_DONE_PERIOD = ("{thing} completed since the last visit",
                     "pichhli visit ke baad {thing} poora",
                     "पिछली विज़िट के बाद {thing} पूर्ण")
CLAIM_STARTED_PERIOD = ("work started on {thing} since the last visit",
                        "pichhli visit ke baad {thing} ka kaam shuru",
                        "पिछली विज़िट के बाद {thing} का कार्य शुरू")
THING: dict[str, tuple[str, str, str]] = {
    "road": ("Road", "sadak", "सड़क"),
    "building": ("Building", "bhawan", "भवन"),
    "drain": ("Drain", "naali", "नाली"),
    "boundary_wall": ("Boundary wall", "chaardiwari", "चारदीवारी"),
    "other": ("Site work", "kaam", "कार्य"),
}
THING_EN = {  # a more specific English name from the MGNREGA sub-category
    # first match wins: specific names first ("cmpond wall" must not read as a "pond")
    "cmpond wall": "School compound wall", "compound wall": "Compound wall",
    "interlocking": "Interlocking tile road", "murram": "Murram road", "cc ": "CC road",
    "cement concrete": "CC road", "kharanja": "Brick (kharanja) road",
    "sanitary complex": "Community sanitary complex", "toilet": "School toilet block",
    "anganwadi": "Anganwadi building", "gp ": "Panchayat building", "workshed": "Workshed",
    "play": "Playground", "water harvesting": "Water harvesting structure", "pond": "Pond",
    "drain": "Drain", "trench": "Water absorption trench", "bund": "Earthen bund",
    "check dam": "Check dam", "sand filter": "Borewell recharge filter",
}


@dataclass
class Item:
    id: str
    split: str
    source: str
    site: str
    district: str
    work_type: str
    image_a: str            # relative to the dataset root
    image_b: str
    claim: str
    claim_kind: str         # reached | period
    lang: str               # en | hinglish | hi
    trick: str
    target: dict = field(default_factory=dict)
    real: bool = True                               # both photos real and unedited
    edits: list = field(default_factory=list)       # paste | relight | darken | occlude
    label_check: str = "auto"                       # auto | eye (checked by looking) | human
    ab_distance: float | None = None    # how different A and B look (DINOv2): scores are also
                                        # split by it, so "identical photos" cannot hide a shortcut

    def prompt(self) -> str:
        return user_prompt(self.work_type, self.claim, self.claim_kind)


def user_prompt(work_type: str, claim: str, claim_kind: str) -> str:
    kind = ("what B shows now" if claim_kind == "reached"
            else "work done between A and B")
    return (f"Work type: {work_type.replace('_', ' ')}. Stages: {' -> '.join(LADDER)}.\n"
            f"Agency's claim ({kind}): \"{claim}\"\n"
            "Reply with JSON only: {\"same_place\": yes|no|unsure, "
            "\"stage_A\": <stage or unknown>, "
            "\"stage_B\": <stage or unknown>, \"permanent_change\": yes|no|cant_tell, "
            "\"verdict\": shown|not_shown|cant_tell, \"reason\": <at most 25 words>}")


def split_of(district: str, test_share: float = 0.15, calib_share: float = 0.07) -> str:
    """Deterministic: a district's hash decides its split, so a district never straddles two."""
    h = int(hashlib.sha256(district.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    if h < test_share:
        return "test"
    if h < test_share + calib_share:
        return "calib"
    return "train"


def thing_of(work_type: str, subcategory: str, lang: str) -> str:
    li = ("en", "hinglish", "hi").index(lang)
    if lang == "en":
        s = f" {subcategory.lower()} "
        for k, v in THING_EN.items():
            if k in s:
                return v
    return THING[work_type][li]


def claim_text(template: tuple[str, str, str], work_type: str, subcategory: str, lang: str) -> str:
    li = ("en", "hinglish", "hi").index(lang)
    thing = thing_of(work_type, subcategory, lang)
    if lang == "en" and not template[li].startswith("{thing}"):
        thing = "the " + thing[0].lower() + thing[1:]        # "work started on the CC road ..."
    t = template[li].format(thing=thing)
    return t[0].upper() + t[1:] if lang != "hi" else t


def reason(work_type: str, a: int | None, b: int | None, trick: str, verdict: str,
           claim_kind: str) -> str:
    look = LOOKS[work_type]
    if trick == "other_site":
        return "Photos A and B show different places, so the claim cannot be judged from them."
    if trick == "dark":
        return "Photo B is too dark to see the work, so the claim cannot be judged."
    if trick == "occluded":
        return "Most of photo B is blocked, so the work cannot be seen."
    if trick == "staged":
        return ("Photo B adds people or vehicles but no new structure; the work looks as in "
                "photo A.")
    if trick == "light":
        return "Only the light differs between A and B; the structure is unchanged."
    if trick == "view":
        return ("Both photos were taken at the same time from different spots; nothing new was "
                "built.")
    if trick == "double_claim":
        return "The work was already complete in photo A, so it was not done in this period."
    if trick == "swapped":
        return f"Photo B shows {look[b]}, less built than photo A; this is not progress."
    sa = look[a] if a is not None else "the site"
    sb = look[b] if b is not None else "the site"
    if verdict == "shown":
        return f"Photo A shows {sa}; photo B shows {sb}, which matches the claim."
    return f"Photo B shows {sb}, which does not match the claim."


def target(same_place: str, a: int | None, b: int | None, change: str, verdict: str,
           why: str) -> dict:
    def name(r: int | None) -> str:
        return LADDER[r] if r is not None else "unknown"

    return {"same_place": same_place, "stage_A": name(a), "stage_B": name(b),
            "permanent_change": change, "verdict": verdict, "reason": why}


# ---- image tricks -------------------------------------------------------------------------------

def load(path: Path, max_side: int = 896) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    h, w = img.shape[:2]
    s = max_side / max(h, w)
    if s < 1:
        img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    return img


def relight(img: np.ndarray, rng: random.Random) -> np.ndarray:
    """Light only: brightness, contrast, white balance, gamma and a shadow band (D2)."""
    x = img.astype(np.float32) / 255
    x = x * rng.uniform(0.55, 1.35) + rng.uniform(-0.08, 0.08)
    x = x * np.array([rng.uniform(0.85, 1.15) for _ in range(3)], np.float32)
    x = np.clip(x, 0, 1) ** rng.uniform(0.7, 1.4)
    h, w = x.shape[:2]
    if rng.random() < 0.6:                          # a shadow band, as a tree or wall would cast
        yy, xx = np.mgrid[0:h, 0:w]
        ang = rng.uniform(0, np.pi)
        d = (xx - w * rng.random()) * np.cos(ang) + (yy - h * rng.random()) * np.sin(ang)
        band = np.abs(d) < rng.uniform(0.08, 0.25) * max(h, w)
        x[band] *= rng.uniform(0.45, 0.7)
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)


def darken(img: np.ndarray, rng: random.Random) -> np.ndarray:
    return (img.astype(np.float32) * rng.uniform(0.03, 0.08)).astype(np.uint8)


def occlude(img: np.ndarray, rng: random.Random) -> np.ndarray:
    """A hand, a bag or a wall in front of the lens: 70-90% of the view blocked."""
    out = img.copy()
    h, w = out.shape[:2]
    share = rng.uniform(0.7, 0.9)
    colour = [rng.randint(10, 90)] * 3
    if rng.random() < 0.5:
        out[: int(h * share)] = colour
    else:
        out[:, : int(w * share)] = colour
    return cv2.GaussianBlur(out, (0, 0), 1.5)


def paste(img: np.ndarray, cutouts: list[np.ndarray], rng: random.Random, n: int) -> np.ndarray:
    """Pastes `n` RGBA cut-outs (people, vehicles, animals) on the lower half of the photo (D5)."""
    out = img.copy()
    h, w = out.shape[:2]
    for _ in range(n):
        c = cutouts[rng.randrange(len(cutouts))]
        target_h = int(h * rng.uniform(0.18, 0.45))
        s = target_h / c.shape[0]
        tw = max(4, int(c.shape[1] * s))
        if tw >= w or target_h >= h:
            continue
        cc = cv2.resize(c, (tw, target_h), interpolation=cv2.INTER_AREA)
        if rng.random() < 0.5:
            cc = cc[:, ::-1]
        y1 = int(rng.uniform(0.5, 1.0) * h)
        y0 = max(0, y1 - target_h)
        x0 = rng.randrange(0, w - tw)
        roi = out[y0:y0 + cc.shape[0], x0:x0 + tw]
        cc = cc[: roi.shape[0], : roi.shape[1]]
        alpha = cv2.GaussianBlur(cc[..., 3].astype(np.float32) / 255, (0, 0), 1.0)[..., None]
        # match the cut-out's brightness to the spot it lands on
        inside = cc[..., 3] > 0
        gain = (roi.mean() + 1) / (cc[..., :3][inside].mean() + 1) if inside.any() else 1
        rgb = np.clip(cc[..., :3].astype(np.float32) * np.clip(gain, 0.6, 1.5), 0, 255)
        out[y0:y0 + cc.shape[0], x0:x0 + cc.shape[1]] = (
            alpha * rgb + (1 - alpha) * roi.astype(np.float32)).astype(np.uint8)
    return out


# ---- items from GeoMGNREGA assets ---------------------------------------------------------------

# "Progress" items only for works whose finished state is an UNMISTAKABLE built structure (owner's
# certainty rule). Found by eye on real assets (8 Oct 2026): a grove's "after" photo differs from
# its "before" by season alone; earth (murram) and gravel roads, ponds, bunds and trenches can
# look much the same before and after; repairs change little. They stay in the data for the real
# "no progress" and "can't tell" items, never as progress.
STRUCTURE = ("anganwadi", "gp for", "gp bhawan", "panchayat", "workshed", "sanitary complex",
             "toilet", "cmpond wall", "compound wall", "boundary wall", "interlocking",
             "cement concrete", "cc road", "kharanja", "drain", "kitchen", "school")
NOT_STRUCTURE = ("repair", "maint", "renov", "play", "murram", "gravel", "earthen", "pond", "bund",
                 "trench", "plantation", "levelling", "desilting")


SAME_VIEW = 0.10   # two photos of one moment closer than this show the same scene (set by eye)


def asset_work_type(asset: dict) -> str:
    """The work type from today's word list (records harvested earlier keep an older guess)."""
    from drishti_vision.geomgnrega import work_type_of
    sub = asset.get("subcategory") or ""
    return work_type_of(str(asset.get("category_id", "")), sub) if sub else asset["work_type"]


def structural(asset: dict) -> bool:
    """A work that adds an unmistakable built structure (see STRUCTURE)."""
    import re
    s = (asset.get("subcategory") or "").lower()
    # whole-word starts: the portal's "CmpOnd wall" must not read as a "pond"
    return (any(re.search(r"\b" + re.escape(w), s) for w in STRUCTURE)
            and not any(re.search(r"\b" + re.escape(w), s) for w in NOT_STRUCTURE))


def _photo(asset: dict, stage: int, n: int) -> str | None:
    for p in asset["photos"]:
        if p["stage"] == stage and p["n"] == n and p.get("file"):
            return p["file"]
    return None


def mgnrega_items(asset: dict, root: Path, photo_rel: str, made_rel: str, rng: random.Random,
                  others: list[dict], cutouts: list[np.ndarray],
                  synthetic: bool = True) -> list[Item]:
    """Every claim-ladder item one asset yields (before 1, during 2, after 3; two photos each),
    under the owner's rules in the module docstring. `asset["change"]` holds change.asset_change's
    verdicts. Image paths are relative to `root` (the data folder on D:): photos under `photo_rel`,
    edited images written under `made_rel`."""
    sub, dist = asset.get("subcategory", ""), asset["district_code"]
    wt = asset_work_type(asset)
    site, split = asset["id"], split_of(dist)
    ch = asset.get("change") or {}
    certain_13 = structural(asset) and bool(ch.get("ok_13"))
    certain_12 = structural(asset) and bool(ch.get("ok_12"))
    allow_edits = synthetic and split == "train"
    ph = {(s, n): _photo(asset, s, n) for s in (1, 2, 3) for n in (1, 2)}
    out: list[Item] = []

    def rel(f: str) -> str:
        return f"{photo_rel}/{f}"

    def add(a_img, b_img, tmpl, kind, trick, tg, edits=()):
        lang = rng.choices(("en", "hinglish", "hi"), (0.6, 0.25, 0.15))[0]
        claim = claim_text(tmpl, wt, sub, lang)
        iid = hashlib.sha1(f"{site}|{a_img}|{b_img}|{claim}|{trick}".encode()).hexdigest()[:16]
        out.append(Item(iid, split, "geomgnrega", site, dist, wt, a_img, b_img, claim, kind, lang,
                        trick, tg, real=not edits, edits=list(edits)))

    def made(name: str, img: np.ndarray) -> str:
        p = root / made_rel / f"{site}_{name}.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return f"{made_rel}/{p.name}"

    s1 = [ph[(1, n)] for n in (1, 2) if ph[(1, n)]]
    s2 = [ph[(2, n)] for n in (1, 2) if ph[(2, n)]]
    s3 = [ph[(3, n)] for n in (1, 2) if ph[(3, n)]]
    if not s1 or not s3:
        return out
    a1, b3 = rel(rng.choice(s1)), rel(rng.choice(s3))

    # REAL, progress certain: not started -> complete
    if certain_13:
        add(a1, b3, CLAIM_DONE_PERIOD, "period", "none",
            target("yes", 0, 2, "yes", "shown", reason(wt, 0, 2, "none", "shown", "period")))
        add(a1, b3, CLAIM_DONE, "reached", "none",
            target("yes", 0, 2, "yes", "shown", reason(wt, 0, 2, "none", "shown", "reached")))
    # REAL, progress certain: not started -> during (at least under way; "complete" never asked)
    if certain_12 and s2:
        add(a1, rel(rng.choice(s2)), CLAIM_STARTED_PERIOD, "period", "none",
            target("yes", 0, None, "yes", "shown",
                   "Photo A shows " + LOOKS[wt][0] + "; photo B shows work done since then."))
    def same_scene(stage: int) -> bool:
        """The two photos of one moment show the same scene, so "nothing was added between
        them" can be read from the photos (a far-apart pair of views cannot say it)."""
        v = ch.get(f"d{stage}{stage}")
        return v is not None and v <= SAME_VIEW

    # REAL, no progress: the two photos of one moment, before the work
    if len(s1) == 2:
        a, b = rel(s1[0]), rel(s1[1])
        if same_scene(1):
            add(a, b, CLAIM_STARTED_PERIOD, "period", "view",
                target("yes", 0, 0, "no", "not_shown",
                       reason(wt, 0, 0, "view", "not_shown", "period")))
        if structural(asset):
            # "is it finished?" is decidable from a before photo only for a structure that
            # would be unmistakable once built (a grove's trench may look the same either way)
            add(a, b, CLAIM_DONE, "reached", "view",
                target("yes", 0, 0, "no", "not_shown",
                       reason(wt, 0, 0, "none", "not_shown", "reached")))
    # REAL, no progress, often a busy site: the two photos of one moment during the work
    if len(s2) == 2 and same_scene(2):
        add(rel(s2[0]), rel(s2[1]), CLAIM_DONE_PERIOD, "period", "busy",
            target("yes", None, None, "no", "not_shown",
                   "Both photos were taken at the same time during the work; nothing was added "
                   "between them."))
    # REAL: already complete in A, so "done this period" is the same work claimed twice
    if len(s3) == 2:
        a, b = rel(s3[0]), rel(s3[1])
        if same_scene(3):
            add(a, b, CLAIM_DONE_PERIOD, "period", "double_claim",
                target("yes", 2, 2, "no", "not_shown",
                       reason(wt, 2, 2, "double_claim", "not_shown", "period")))
        if certain_13:      # the after photo shows finished work only where the change was certain
            add(a, b, CLAIM_DONE, "reached", "none",
                target("yes", 2, 2, "no", "shown", f"Photo B shows {LOOKS[wt][2]}, as claimed."))
    # REAL photos in reverse order: B is the before photo (direction)
    if certain_13:
        add(b3, a1, CLAIM_DONE_PERIOD, "period", "swapped",
            target("yes", 2, 0, "no", "not_shown",
                   reason(wt, 2, 0, "swapped", "not_shown", "period")))
    # REAL: B is a clearly different place (an asset of ANOTHER work type, same split)
    # B must be unmistakably another place: a finished structure of another work type (a green
    # plot next to a green grove could pass for one place; found by eye, 8 Oct 2026)
    other = [o for o in others if asset_work_type(o) != wt and o["id"] != site and structural(o)
             and (o.get("change") or {}).get("ok_13")
             and split_of(o["district_code"]) == split]
    if other:
        o = rng.choice(other)
        ob = _photo(o, 3, 1) or _photo(o, 3, 2)
        if ob:
            add(a1, rel(ob), CLAIM_DONE_PERIOD, "period", "other_site",
                target("no", 0, None, "cant_tell", "cant_tell",
                       reason(wt, None, None, "other_site", "cant_tell", "period")))
    for it in out:      # how different the two real photos look (scores are split by it)
        key = {"view": "d11", "busy": "d22", "double_claim": "d33", "swapped": "d13"}.get(it.trick)
        if it.trick == "none":
            key = "d13" if it.claim_kind == "period" or "/s1_" in it.image_a else "d33"
            key = "d12" if "/s2_" in it.image_b else key
        it.ab_distance = ch.get(key) if key else None
    if not allow_edits:
        return out
    # EDITED (training only); every edit also goes into a real progress pair labelled shown
    if cutouts:
        n = rng.randint(2, 5)
        add(a1, made("staged_no", paste(load(root / a1), cutouts, rng, n)),
            rng.choice((CLAIM_DONE_PERIOD, CLAIM_STARTED_PERIOD)), "period", "staged",
            target("yes", 0, 0, "no", "not_shown",
                   reason(wt, 0, 0, "staged", "not_shown", "period")), edits=("paste",))
        if certain_13:
            add(a1, made("staged_yes", paste(load(root / b3), cutouts, rng, n)),
                CLAIM_DONE_PERIOD, "period", "none",
                target("yes", 0, 2, "yes", "shown", reason(wt, 0, 2, "none", "shown", "period")),
                edits=("paste",))
    add(a1, made("light_no", relight(load(root / a1), rng)), CLAIM_STARTED_PERIOD, "period",
        "light", target("yes", 0, 0, "no", "not_shown",
                        reason(wt, 0, 0, "light", "not_shown", "period")), edits=("relight",))
    if certain_13:
        add(a1, made("light_yes", relight(load(root / b3), rng)), CLAIM_DONE_PERIOD, "period",
            "none", target("yes", 0, 2, "yes", "shown",
                           reason(wt, 0, 2, "none", "shown", "period")), edits=("relight",))
    if rng.random() < 0.5:
        add(a1, made("dark", darken(load(root / b3), rng)), CLAIM_DONE_PERIOD, "period", "dark",
            target("unsure", 0, None, "cant_tell", "cant_tell",
                   reason(wt, None, None, "dark", "cant_tell", "period")), edits=("darken",))
    else:
        add(a1, made("occluded", occlude(load(root / b3), rng)), CLAIM_DONE, "reached",
            "occluded", target("unsure", 0, None, "cant_tell", "cant_tell",
                               reason(wt, None, None, "occluded", "cant_tell", "reached")),
            edits=("occlude",))
    return out


def build_mgnrega(assets_jsonl: str | Path, root: str | Path, photo_rel: str, made_rel: str,
                  cutouts: list[np.ndarray], seed: int = 0, synthetic: bool = True) -> list[Item]:
    """Items for every asset in `assets_jsonl` (each with its "change" scores, change.py); paths
    relative to `root` (see mgnrega_items)."""
    root = Path(root)
    rng = random.Random(seed)
    assets = [json.loads(line) for line in
              Path(assets_jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]
    items: list[Item] = []
    for a in assets:
        try:
            items += mgnrega_items(a, root, photo_rel, made_rel, rng, assets, cutouts, synthetic)
        except FileNotFoundError:
            continue
    return items


# ---- items from still-camera timelapses (T146's build with --keep-raw) --------------------------

TL_PROGRESS_SHARE = 0.15    # a certain progress pair: at least this share of the known view is
                            # permanent work by the hindsight teacher (its own floor is 0.02)
TL_MIN_GAP = 0.25           # ... and the frames at least this share of the shot apart
TL_BUSY = 0.03              # a no-progress pair whose B has this share of moving things: "busy"
TL_KNOWN = 0.8              # a no-progress pair: the teacher judged at least this share of the view
                            # (pavers laid under moving workers sat in the unjudged rest; by eye,
                            # 8 Oct 2026)
TL_MAX_NOISE = 0.4          # a shot whose frames 3-5 apart already differ this much (its `lo`,
                            # hindsight.calibrate) is hand-held, cut or dissolving: its teacher
                            # calls nearly everything unchanged and found no progress in any such
                            # test shot, so it gives no items (by eye, 8 Oct 2026: every shot
                            # below it read right)
TL_CLAIM = ("New construction work done since the last visit",
            "pichhli visit ke baad naya nirmaan kaam hua",
            "पिछली विज़िट के बाद नया निर्माण कार्य हुआ")


def timelapse_items(data: str | Path, root: str | Path, frames_rel: str, rng: random.Random,
                    per_shot: int = 12) -> list[Item]:
    """Real timelapse pairs, as filmed (the build's `raw` frames), under the owner's certainty
    rule: "shown" only where the hindsight teacher found lasting work over a large share of the
    view and a long gap; "not_shown" only where it found NO lasting change at all, judged over
    most of the view (TL_KNOWN), and the pair does not span any stretch of the shot where the
    teacher found work (busy when people or machines move in B, light otherwise); swapped
    progress pairs are not shown. Shots from a shaky or cut camera (TL_MAX_NOISE) give no items.
    Each pair of frames is used once. Frames are saved in their
    own colours (the build keeps them RGB; OpenCV writes BGR)."""
    data, root = Path(data), Path(root)
    out: list[Item] = []
    shots = [json.loads(line) for line in (data / "shots.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    for s in shots:
        sid = s["shot_id"]
        if s.get("lo", 0.0) > TL_MAX_NOISE:
            continue
        lab_p, shot_p = data / "labels" / f"{sid}.npz", data / "shots" / f"{sid}.npz"
        if not lab_p.exists() or not shot_p.exists():
            continue
        shot = np.load(shot_p)
        if "raw" not in shot:
            continue
        raw, act = shot["raw"], shot["activity"].astype(np.float32)
        lab = np.load(lab_p)
        T = len(raw)
        wt = s.get("work_type", "other")
        wt = wt if wt in LOOKS else "other"
        rows = list(zip(lab["a"], lab["b"], lab["label"], lab["kind"], lab["patches"],
                        strict=True))
        work = [(int(a), int(b)) for a, b, y, k, pt in rows      # stretches with lasting work
                if int(k) != 2 and (y == 1 or (pt == 1).any())]
        chosen: list[tuple[int, int, str, str]] = []
        seen: set[tuple[int, int]] = set()
        for a, b, y, k, pt in rows:
            a, b = int(a), int(b)
            if (a, b) in seen:
                continue
            seen.add((a, b))
            kind = ("forward", "short", "swapped")[int(k)]
            known = pt != -1
            share = float((pt == 1).sum() / known.sum()) if known.any() else 0.0
            if kind == "forward" and y == 1 and share >= TL_PROGRESS_SHARE \
                    and (b - a) >= TL_MIN_GAP * T:
                chosen.append((a, b, "none", "shown"))
                chosen.append((b, a, "swapped", "not_shown"))
            elif kind in ("forward", "short") and y == 0 and not (pt == 1).any() \
                    and float(known.mean()) >= TL_KNOWN \
                    and not any(a <= wa and wb <= b for wa, wb in work):
                busy = float(act[b].mean()) >= TL_BUSY
                chosen.append((a, b, "busy" if busy else "light", "not_shown"))
        rng.shuffle(chosen)
        for a, b, trick, verdict in chosen[:per_shot]:
            paths = []
            for t in (a, b):
                p = root / frames_rel / sid / f"f{t:03d}.jpg"
                if not p.exists():
                    p.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(p), np.ascontiguousarray(raw[t][..., ::-1]),
                                [cv2.IMWRITE_JPEG_QUALITY, 92])
                paths.append(f"{frames_rel}/{sid}/f{t:03d}.jpg")
            lang = rng.choices(("en", "hinglish", "hi"), (0.6, 0.25, 0.15))[0]
            claim = TL_CLAIM[("en", "hinglish", "hi").index(lang)]
            change = "yes" if verdict == "shown" else "no"
            why = {"none": "Photo B shows permanent structure that was not there in photo A.",
                   "swapped": "Photo B is less built than photo A; this is not progress.",
                   "busy": "People or machines moved, but no permanent structure was added.",
                   "light": "Only the light differs; the structure is unchanged."}[trick]
            iid = hashlib.sha1(f"{sid}|{a}|{b}|{claim}".encode()).hexdigest()[:16]
            out.append(Item(iid, s.get("split", "train"), "timelapse", s.get("site_id", sid),
                            s.get("channel", ""), wt, paths[0], paths[1], claim, "period", lang,
                            trick, target("yes", None, None, change, verdict, why)))
    return out


def write_items(items: list[Item], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(asdict(it), ensure_ascii=False) + "\n")


def read_items(path: str | Path) -> list[Item]:
    return [Item(**json.loads(line)) for line in
            Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def card(items: list[Item]) -> str:
    """Counts by split, trick and verdict: the dataset card's numbers (H8)."""
    lines = ["# Claim-ladder items (T153)", ""]
    for sp in ("train", "calib", "test"):
        its = [i for i in items if i.split == sp]
        if not its:
            continue
        v = Counter(i.target["verdict"] for i in its)
        t = Counter(i.trick for i in its)
        w = Counter(i.work_type for i in its)
        lines += [f"## {sp}: {len(its)} items, {len({i.site for i in its})} assets, "
                  f"{len({i.district for i in its})} districts", "",
                  "- verdicts: " + ", ".join(f"{k} {v[k]}" for k in VERDICTS),
                  "- tricks: " + ", ".join(f"{k} {t[k]}" for k in TRICKS if t[k]),
                  "- work types: " + ", ".join(f"{k} {n}" for k, n in w.most_common()),
                  "- languages: " + ", ".join(f"{k} {n}" for k, n in
                                              Counter(i.lang for i in its).most_common()),
                  f"- real, unedited photos: {sum(i.real for i in its)} of {len(its)}", ""]
    return "\n".join(lines)
