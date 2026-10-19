"""Build the DRISHTI SIH 2026 idea deck (v3) pages for the ppt-master round-trip workspace.

Reads the untouched template pages in _template_svgs/, keeps every chrome object
(SIH logo, team oval, title, blue footer, page number) as imported, fills the title
and team name, removes the template's placeholder text, and appends DRISHTI's
content as compact SVG that ppt-master exports as native, editable PowerPoint shapes.

Every number on a slide is listed with its source in CONTENT_PLAN.md.

    python3 build_slides.py            # writes authoring-svg-flat/slide_01..06.svg
"""
from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SRC = HERE / "_template_svgs"
OUT = HERE / "authoring-svg-flat"

# ---------------------------------------------------------------- design tokens
NAVY = "#0B3D6E"      # headings, structure
BLUE = "#0070C0"      # template footer blue; links, "tested" status
SAFFRON = "#E8871E"   # markers and focal fills (echoes the SIH logo)
SAFF_TX = "#B35900"   # saffron for text (readable on white)
GREEN = "#1E7B45"     # "live" status (echoes the SIH logo)
INK = "#1D2939"
BODY = "#344054"
MUTED = "#667085"
RULE = "#D0D5DD"
PANEL = "#F2F5F9"
BLUE_T = "#E8F1FA"
SAFF_T = "#FDF1E4"
GREEN_T = "#E7F4EC"
WHITE = "#FFFFFF"
FONT = "Calibri"

# ---------------------------------------------------------------- text metrics
_NARROW = set("iljtfrI.,:;'|!()[] ")
_WIDE = set("mwMW@%")


def est_width(text: str, size: float, bold: bool = False) -> float:
    """Rough Calibri advance width, good enough to choose line breaks."""
    w = 0.0
    for ch in text:
        if ch in _NARROW:
            w += 0.27
        elif ch in _WIDE:
            w += 0.80
        elif ch.isupper() or ch.isdigit() or ch in "₹–—→":
            w += 0.56
        else:
            w += 0.48
    return w * size * (1.06 if bold else 1.0)


def wrap(text: str, width: float, size: float, bold: bool = False) -> list[str]:
    if " " not in text and "/" in text and est_width(text, size, bold) > width:   # a URL: break after slashes
        lines, cur = [], ""
        for seg in [t + "/" for t in text.split("/")[:-1]] + [text.split("/")[-1]]:
            if cur and est_width(cur + seg, size, bold) > width:
                lines.append(cur)
                cur = seg
            else:
                cur += seg
        return lines + ([cur] if cur else [])
    words, lines, cur = text.split(" "), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if cur and est_width(trial, size, bold) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    # a "·" separator never starts or ends a line (it reads as a bullet there)
    lines = [ln[2:] if ln.startswith("· ") else ln for ln in lines]
    return [ln[:-2] if ln.endswith(" ·") else ln for ln in lines]


# ---------------------------------------------------------------- SVG helpers
def attrs(**kw) -> str:
    out = []
    for k, v in kw.items():
        if v is None:
            continue
        out.append(f'{k.replace("_", "-")}="{v}"')
    return " ".join(out)


def rect(x, y, w, h, fill=WHITE, stroke=None, rx=6, sw=1, dash=None) -> str:
    a = attrs(x=r2(x), y=r2(y), width=r2(w), height=r2(h), rx=rx if rx else None, fill=fill,
              stroke=stroke, stroke_width=sw if stroke else None, stroke_dasharray=dash)
    return f"<rect {a}/>"


def line(x1, y1, x2, y2, stroke=RULE, sw=1, dash=None, marker=None) -> str:
    m = f' marker-end="url(#{marker})"' if marker else ""
    a = attrs(x1=r2(x1), y1=r2(y1), x2=r2(x2), y2=r2(y2), stroke=stroke, stroke_width=sw,
              stroke_dasharray=dash)
    return f"<line {a}{m}/>"


def path(d, stroke=MUTED, sw=1.2, fill="none", dash=None, marker=None) -> str:
    m = f' marker-end="url(#{marker})"' if marker else ""
    return f'<path {attrs(d=d, fill=fill, stroke=stroke, stroke_width=sw, stroke_dasharray=dash)}{m}/>'


def r2(v) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def run(text: str, **style) -> str:
    """One inline run. style keys: fill, weight, size, italic."""
    a = attrs(fill=style.get("fill"), font_weight=style.get("weight"),
              font_size=style.get("size"), font_style="italic" if style.get("italic") else None)
    return f"<tspan {a}>{escape(text)}</tspan>" if a else f"<tspan>{escape(text)}</tspan>"


def text(x, y, lines, size=13, fill=BODY, weight=None, lh=None, anchor=None, italic=False) -> str:
    """One paragraph. `lines` items are plain strings or lists of run() strings."""
    lh = lh or round(size * 1.3, 1)
    head = attrs(x=r2(x), y=r2(y), font_size=size, fill=fill, font_weight=weight,
                 text_anchor=anchor, font_style="italic" if italic else None)
    body = []
    for i, ln in enumerate(lines):
        inner = "".join(ln) if isinstance(ln, list) else escape(ln)
        body.append(f'<tspan x="{r2(x)}" dy="{0 if i == 0 else lh}">{inner}</tspan>')
    return f"<text {head}>{''.join(body)}</text>"


def group(gid, bounds, *parts, font=True) -> str:
    x, y, w, h = bounds
    f = f' font-family="{FONT}"' if font else ""
    return (f'<g id="{gid}" data-pptx-bounds="{r2(x)} {r2(y)} {r2(w)} {r2(h)}"{f}>\n  '
            + "\n  ".join(parts) + "\n</g>")


def diamond(cx, cy, r=5, fill=SAFFRON) -> str:
    return f'<polygon points="{cx},{cy - r} {cx + r},{cy} {cx},{cy + r} {cx - r},{cy}" fill="{fill}"/>'


def pointer(x, y, label, width, size=15) -> tuple[str, float]:
    """Template pointer heading, kept word for word: saffron diamond + navy bold text + rule."""
    lines = wrap(label, width - 16, size, bold=True)
    lh = round(size * 1.2, 1)
    parts = [diamond(x + 5, y - size * 0.33), text(x + 16, y, lines, size, NAVY, "bold", lh)]
    bottom = y + lh * (len(lines) - 1) + 7
    parts.append(line(x, bottom, x + width, bottom, RULE, 1))
    return "".join(parts), bottom


def bullet_list(x, y, items, width, size=13, gap=5, lh=None, marker=SAFFRON) -> tuple[list[str], float]:
    """Each item: plain string (wrapped) or a list of lines of runs. Returns parts and next y."""
    lh = lh or round(size * 1.3, 1)
    parts = []
    for it in items:
        lines = wrap(it, width - 13, size) if isinstance(it, str) else it
        parts.append(f'<circle cx="{r2(x + 3)}" cy="{r2(y - size * 0.32)}" r="2.3" fill="{marker}"/>')
        parts.append(text(x + 13, y, lines, size, BODY, lh=lh))
        y += lh * len(lines) + gap
    return parts, y


def rich_wrap(segments, width, size) -> list[list[str]]:
    """Wrap [(text, style), ...] into lines of runs, keeping each segment's style."""
    lines, cur, cur_w = [], [], 0.0
    for seg_text, style in segments:
        bold = style.get("weight") == "bold"
        for i, word in enumerate(seg_text.split(" ")):
            if word == "":
                continue
            piece = word if not cur else " " + word
            w = est_width(piece, size, bold)
            if cur and cur_w + w > width:
                lines.append(cur)
                cur, cur_w = [], 0.0
                piece, w = word, est_width(word, size, bold)
            cur.append(run(piece, **style))
            cur_w += w
    if cur:
        lines.append(cur)
    return lines


STATUS = {
    "live": ("LIVE", GREEN, WHITE, GREEN),
    "tested": ("TESTED", BLUE, WHITE, BLUE),
    "weak": ("WEAK", WHITE, SAFF_TX, SAFFRON),
    "off": ("OFF", WHITE, MUTED, MUTED),
    "demo": ("DEMO", WHITE, MUTED, MUTED),
    "planned": ("PLANNED", WHITE, MUTED, MUTED),
}


def pill(x, y, kind, w=52, h=16) -> str:
    label, fill, tx, stroke = STATUS[kind]
    return (rect(x, y, w, h, fill, stroke, rx=8, sw=1)
            + text(x + w / 2, y + h - 4.5, [label], 9.5, tx, "bold", anchor="middle"))


def dot(cx, cy, kind, r=4) -> str:
    if kind == "live":
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{GREEN}"/>'
    if kind == "tested":
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{BLUE}"/>'
    return f'<circle cx="{cx}" cy="{cy}" r="{r - 0.5}" fill="{WHITE}" stroke="{MUTED}" stroke-width="1.2"/>'


ARROW_DEFS = (
    '<marker id="arrMuted" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
    f'<polygon points="0 0, 8 3, 0 6" fill="{MUTED}"/></marker>'
    '<marker id="arrNavy" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
    f'<polygon points="0 0, 8 3, 0 6" fill="{NAVY}"/></marker>'
    '<marker id="arrGreen" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
    f'<polygon points="0 0, 8 3, 0 6" fill="{GREEN}"/></marker>'
    '<marker id="arrSaff" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
    f'<polygon points="0 0, 8 3, 0 6" fill="{SAFFRON}"/></marker>'
)


# ---------------------------------------------------------------- template surgery
def load(n: int) -> str:
    return (SRC / f"slide_{n:02d}.svg").read_text(encoding="utf-8")


def drop_group(svg: str, gid: str) -> str:
    new, k = re.subn(rf'<g id="{re.escape(gid)}"[^>]*>.*?</g>\s*', "", svg, count=1, flags=re.S)
    assert k == 1, gid
    return new


def sub_once(svg: str, old: str, new: str) -> str:
    assert svg.count(old) == 1, (old, svg.count(old))
    return svg.replace(old, new)


def add_defs(svg: str, defs: str) -> str:
    if "<defs>" in svg:
        return svg.replace("<defs>", "<defs>" + defs, 1)
    return re.sub(r"(<svg[^>]*>)", r"\1<defs>" + defs.replace("\\", "\\\\") + "</defs>", svg, count=1)


def finish(svg: str, content: list[str], defs: str = "") -> str:
    if defs:
        svg = add_defs(svg, defs)
    head, tail = svg.rsplit("</svg>", 1)       # the root's closing tag only (pictures nest <svg>)
    return head + "\n" + "\n".join(content) + "\n</svg>" + tail


TEAM_OLD = ">Your Team Name</text>"
TEAM_NEW = ' font-weight="bold" fill="#0B3D6E">NeuralNexus</text>'


def set_team(svg: str) -> str:
    # the oval text element: keep the element, replace its words (and make them navy bold)
    m = re.search(r'(<text [^>]*?)( fill="#000000")?>Your Team Name</text>', svg)
    assert m, "team oval"
    head = m.group(1).replace(' font-size="24"', ' font-size="21"')
    return svg.replace(m.group(0), head + TEAM_NEW)


# ================================================================= SLIDE 1 — title
def slide1() -> str:
    svg = load(1)
    svg = drop_group(svg, "shape-10")          # template bullet list (re-authored below)
    svg = sub_once(svg, ">TITLE PAGE</text>", ">DRISHTI</text>")
    svg = svg.replace('font-size="24" fill="#000000" font-weight="bold">DRISHTI</text>',
                      'font-size="54" fill="#0B3D6E" font-weight="bold">DRISHTI</text>')
    svg = svg.replace('x="578.78" y="122.1" text-anchor="middle" xml:space="preserve" font-family="&quot;Times New Roman&quot;, sans-serif" font-size="54"',
                      'x="578.78" y="150" text-anchor="middle" xml:space="preserve" font-family="&quot;Times New Roman&quot;, sans-serif" font-size="54"')

    tag = group("tagline", (230, 162, 700, 58),
                text(578.78, 184, ["The AI-eye on every MPLADS rupee"], 22, NAVY, italic=True, anchor="middle"),
                text(578.78, 208, ["AI checks on every MPLADS work — flags what needs checking, with the evidence"],
                     14.5, MUTED, anchor="middle"))

    fields = [
        ("Problem Statement ID –", "SIH26102"),
        ("Problem Statement Title-", "Development of an AI-powered system to detect anomalies, fraud, and "
                                     "inefficiencies in MPLAD Scheme implementation regd."),
        ("Organisation-", "Ministry of Statistics & Programme Implementation (MoSPI)"),
        ("Theme-", "Smart Automation"),
        ("PS Category-", "Software"),
        ("Team ID-", "121911"),
        ("Team Name-", "NeuralNexus"),
    ]
    x0, y, lab_w, val_x, val_w = 44, 262, 206, 262, 400
    parts = []
    for i, (lab, val) in enumerate(fields):
        vlines = wrap(val, val_w, 17)
        parts.append(f'<circle cx="{x0 + 4}" cy="{y - 6}" r="3" fill="{SAFFRON}"/>')
        parts.append(text(x0 + 16, y, [lab], 17, INK, "bold"))
        parts.append(text(val_x, y, vlines, 17, BODY, lh=22))
        y += 22 * len(vlines) + 16
        if i < len(fields) - 1:
            parts.append(line(x0, y - 22, x0 + 620, y - 22, RULE, 0.8))
    info = group("ps-details", (34, 236, 640, y - 236), *parts)

    logo = group("drishti-mark", (366, 96, 92, 72),
                 f'<image href="../images/drishti_icon_t.png" x="368" y="98" width="86" height="70" preserveAspectRatio="xMidYMid meet"/>')
    return finish(svg, [logo, tag, info])


# ================================================================= SLIDE 2 — idea
def slide2() -> str:
    svg = load(2)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-15362")        # template pointer text (re-authored below, word for word)
    svg = sub_once(svg, '<tspan x="595.21" dy="57.6">IDEA TITLE</tspan>',
                   '<tspan x="595.21" dy="57.6"><tspan>DRISHTI</tspan><tspan font-size="24" font-weight="normal" '
                   'font-style="italic" fill="#344054">  ·  the AI-eye on every MPLADS rupee</tspan></tspan>')
    content = []

    # -- Proposed solution statement
    p, bottom = pointer(32, 146, "Proposed Solution (Describe your Idea/Solution/Prototype)", 1216)
    stmt = rich_wrap([
        ("DRISHTI is a read-only AI layer on top of eSAKSHI.", {"weight": "bold", "fill": INK}),
        ("12 specialist agents check every MPLADS work at every stage, read the certificates, bills and "
         "geo-tagged photos already uploaded to eSAKSHI, and turn what they find into a short, ranked "
         "inspection list for District Authorities — every flag with its evidence and the guideline clause.", {}),
    ], 1210, 14.5)
    content.append(group("solution", (30, 128, 1220, 72), p, text(32, bottom + 18, stmt, 14.5, BODY, lh=19)))

    # -- life-of-a-work band
    top, h = 214, 158
    stages = [
        ("1", "BEFORE SANCTION", [("Eligibility", "forbidden works", "tested"),
                                  ("Duplicate & Split", "repeats, split-ups", "tested"),
                                  ("Cost", "inflated estimates", "live")]),
        ("2", "DURING CONSTRUCTION", [("Site Progress", "claim vs photo, plaque", "planned"),
                                      ("Photo Forensics", "reused photos", "tested"),
                                      ("Geo-Location", "where & when shot", "tested"),
                                      ("Document", "papers that don't add up", "tested"),
                                      ("Satellite", "big works only", "planned")]),
        ("3", "MONEY & TIME", [("Delay", "stuck works, late offices", "tested"),
                               ("Fund Flow", "money left waiting", "tested"),
                               ("Contractor", "a few firms win all", "tested")]),
        ("4", "AFTER COMPLETION", [("Citizen Verification", "asset exists, in use", "planned")]),
    ]
    band = [text(32, top - 4, ["12 AGENTS ACROSS THE LIFE OF A WORK"], 11, MUTED, "bold")]
    cw, gap, x = 226, 10, 32
    for num, name, agents in stages:
        band.append(rect(x, top + 4, cw, h, WHITE, RULE, rx=6))
        band.append(rect(x, top + 4, cw, 26, NAVY, None, rx=6))
        band.append(rect(x, top + 20, cw, 10, NAVY, None, rx=0))
        band.append(f'<circle cx="{x + 16}" cy="{top + 17}" r="8" fill="{SAFFRON}"/>')
        band.append(text(x + 16, top + 21, [num], 11, WHITE, "bold", anchor="middle"))
        band.append(text(x + 30, top + 21.5, [name], 12, WHITE, "bold"))
        ay = top + 50
        for a, what, st in agents:
            band.append(dot(x + 14, ay - 4, st))
            band.append(text(x + 24, ay, [[run(a, weight="bold", fill=INK), run("  " + what, fill=MUTED, size=11.5)]], 12.5))
            ay += 23
        x += cw + gap
    # arrow to the outcome column
    band.append(line(x - gap + 2, top + 4 + h / 2, x + 22, top + 4 + h / 2, NAVY, 1.6, marker="arrNavy"))
    ox, ow = x + 28, 1248 - (x + 28)
    band.append(text(ox, top - 4, ["THEN, FOR EVERY WORK"], 11, MUTED, "bold"))
    steps = [("Risk Fusion", "one 0–100 score, parts add up", SAFF_T, SAFFRON),
             ("Review queue", "ranked by risk × money", WHITE, NAVY),
             ("Inspection plan", "the 10% of visits (para 6.4)", WHITE, NAVY)]
    sy = top + 4
    for i, (t1, t2, fill, stroke) in enumerate(steps):
        band.append(rect(ox, sy, ow, 44, fill, stroke, rx=6, sw=1.2))
        band.append(text(ox + 10, sy + 18, [t1], 13, INK, "bold"))
        band.append(text(ox + 10, sy + 34, [t2], 11.5, MUTED))
        if i < 2:
            band.append(line(ox + ow / 2, sy + 44, ox + ow / 2, sy + 55, NAVY, 1.2, marker="arrNavy"))
        sy += 57
    # legend
    ly = top + h + 22
    leg = [dot(40, ly - 4, "live"), text(49, ly, ["Live in the prototype"], 11, MUTED),
           dot(172, ly - 4, "tested"), text(181, ly, ["Tested on real eSAKSHI works, being moved into the live engine"], 11, MUTED),
           dot(508, ly - 4, "planned"), text(517, ly, ["Planned / not yet testable on public data"], 11, MUTED)]
    content.append(group("life-of-a-work", (30, 198, 1220, 198), *band, *leg))

    # -- three pointer columns
    ty = 426
    cols = [(32, 392), (440, 392), (856, 392)]

    c1, b1 = pointer(cols[0][0], ty, "Detailed explanation of the proposed solution", cols[0][1])
    parts1, _ = bullet_list(cols[0][0], b1 + 20, [
        "Each agent answers one plain question — e.g. “Was this photo already used on another work?”",
        "Reads what eSAKSHI already holds: 2,09,993 works plus the completion and utilisation certificates, "
        "bills and site photos uploaded for them.",
        "Risk Fusion adds the agents into one 0–100 score. The parts add up exactly, so an officer sees why.",
        "Next: officers' verdicts from each visit become labels that retrain the agents.",
    ], cols[0][1], 12.5, gap=6)
    content.append(group("col-explanation", (30, 408, 396, 250), c1, *parts1))

    c2, b2 = pointer(cols[1][0], ty, "How it addresses the problem", cols[1][1])
    pairs = [
        ("4,918 works had no MPLADS plaque", "CAG audit, 31 districts", "Plaque and photo checks at every work"),
        ("₹279.99 cr stuck in 12,006 incomplete works", "CAG audit, 71 districts", "Stuck-work list + each office's track record"),
        ("Sanction is due within 75 days", "Guidelines ¶3.12", "Flags works left waiting past the limit"),
        ("District must inspect ≥10% of works", "Guidelines ¶6.4", "Risk-ranked list of which works to visit"),
    ]
    py, parts2 = b2 + 20, []
    for prob, src, ans in pairs:
        parts2.append(text(cols[1][0], py, [[run(prob, fill=INK, weight="bold"), run("  " + src, fill=MUTED, size=11)]], 12.5))
        parts2.append(text(cols[1][0] + 4, py + 17, [[run("→ ", fill=SAFF_TX, weight="bold"), run(ans, fill=BODY)]], 12.5))
        py += 50
    content.append(group("col-problem", (438, 408, 396, 250), c2, *parts2))

    c3, b3 = pointer(cols[2][0], ty, "Innovation and uniqueness of the solution", cols[2][1])
    parts3, _ = bullet_list(cols[2][0], b3 + 20, [
        "Reads the GPS stamp printed into site photos. eSAKSHI strips the phone's own GPS data (0 of 321 photos kept it).",
        "Proof before launch: an agent goes live only after it meets its accuracy target on real eSAKSHI works.",
        "Never accuses. It says “needs checking”, cites the guideline clause, and shows “could not assess” honestly.",
        "Reads typed certificates with free, on-server text reading; paid AI only for Hindi and handwritten papers.",
    ], cols[2][1], 12.5, gap=6)
    content.append(group("col-innovation", (854, 408, 396, 250), c3, *parts3))

    return finish(svg, content, ARROW_DEFS)


# ================================================================= SLIDE 3 — technical approach
def slide3() -> str:
    svg = load(3)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-17410")
    content = []

    # -- technologies (left)
    lx, lw = 32, 392
    p, b = pointer(lx, 142, "Technologies to be used (e.g. programming languages, frameworks, hardware)", lw)
    rows = [
        ("Frontend", "Next.js 16 · React 19 · Tailwind CSS 4 · MapLibre maps"),
        ("Backend & API", "Python 3.12 · FastAPI · role-based sign-in (Supabase Auth)"),
        ("Database", "PostgreSQL on Supabase, Mumbai region"),
        ("ML & statistics", "LightGBM · scikit-learn · pandas · NumPy"),
        ("Photos & papers", "OpenCV feature matching · 256-bit photo fingerprints · RapidOCR + PyMuPDF text reading"),
        ("AI reading", "Gemini vision for Hindi / handwritten papers and site progress (planned, capped)"),
        ("Maps & places", "Official LGD district outlines · India Post PIN codes · DIGIPIN grid (planned)"),
        ("Hosting & CI", "Vercel · GitHub Actions runs every test on each push"),
        ("Security & privacy", "Secrets only in server settings · district scoping inside every database query · "
                               "phone and bank numbers masked"),
        ("Hardware", "None to buy — officers use a browser or a phone"),
    ]
    wrapped = []
    for k, v in rows:
        vl = [ln[2:] if ln.startswith("· ") else ln for ln in wrap(v, lw - 132, 12.5)]
        wrapped.append((k, [ln[:-2] if ln.endswith(" ·") else ln for ln in vl]))
    natural = sum(16.5 * len(vl) + 8 for _, vl in wrapped)
    pad = max(8, (660 - (b + 8) - natural) / len(wrapped) + 8)
    ry, parts = b + 8, []
    for i, (k, vl) in enumerate(wrapped):
        rh = 16.5 * len(vl) + pad
        if i % 2 == 0:
            parts.append(rect(lx, ry, lw, rh, PANEL, None, rx=0))
        base = ry + pad / 2 + 12
        parts.append(text(lx + 8, base, [k], 12.5, NAVY, "bold"))
        parts.append(text(lx + 124, base, vl, 12.5, BODY, lh=16.5))
        ry += rh
    content.append(group("tech-stack", (30, 124, 396, ry - 124 + 2), p, *parts))

    # -- methodology flow (right)
    rx0, rw = 452, 796
    p2, b2 = pointer(rx0, 142, "Methodology and process for implementation (Flow Charts/Images/ working prototype)", rw)
    content.append(group("method-heading", (450, 124, 800, b2 - 124 + 4), p2))

    fy, fh = b2 + 26, 96
    nodes = [  # (x, w, title, sub-lines, fill, stroke)
        (rx0, 120, "eSAKSHI data", ["2,09,993 works", "certificates, bills,", "site photos"], PANEL, MUTED),
        (rx0 + 142, 128, "Data Validation", ["dates & amounts", "reads papers, stamps", "masks phone & bank nos."], WHITE, NAVY),
        (rx0 + 292, 214, "12 agents", [], WHITE, NAVY),
        (rx0 + 528, 110, "Risk Fusion", ["0–100 score", "top reasons", "parts add up"], SAFF_T, SAFFRON),
        (rx0 + 660, 136, "Review queue", ["Ministry · District ·", "Field dashboards", "evidence + clause"], WHITE, NAVY),
    ]
    flow = []
    for i in range(len(nodes) - 1):     # arrows first, boxes on top
        x_end = nodes[i][0] + nodes[i][1]
        x_next = nodes[i + 1][0]
        flow.append(line(x_end + 1, fy + fh / 2, x_next - 2, fy + fh / 2, NAVY, 1.4, marker="arrNavy"))
    for x, w, t, subs, fill, stroke in nodes:
        flow.append(rect(x, fy, w, fh, fill, stroke, rx=6, sw=1.2))
        flow.append(text(x + w / 2, fy + 22, [t], 13.5, INK, "bold", anchor="middle"))
        if subs:
            flow.append(text(x + w / 2, fy + 42, subs, 11, MUTED, lh=15, anchor="middle"))
    ax = rx0 + 292
    chips = [("Before sanction", "3"), ("Construction", "5"), ("Money & time", "3"), ("After completion", "1")]
    for i, (c, n) in enumerate(chips):
        cx = ax + 10 + (i % 2) * 100
        cy = fy + 34 + (i // 2) * 30
        flow.append(rect(cx, cy, 94, 24, BLUE_T, None, rx=4))
        flow.append(text(cx + 6, cy + 16, [[run(n + "  ", weight="bold", fill=NAVY), run(c, fill=BODY, size=10)]], 11))
    # officer verdict + feedback loop
    ox, ow, oy = rx0 + 660, 136, fy + fh + 34
    flow.append(line(ox + ow / 2, fy + fh + 1, ox + ow / 2, oy - 2, NAVY, 1.4, marker="arrNavy"))
    flow.append(rect(ox, oy, ow, 44, GREEN_T, GREEN, rx=6, sw=1.2))
    flow.append(text(ox + ow / 2, oy + 18, ["Officer verdict"], 13, INK, "bold", anchor="middle"))
    flow.append(text(ox + ow / 2, oy + 34, ["the human decides"], 11, MUTED, anchor="middle"))
    back_y = oy + 22
    loop_x = ax + 107
    flow.append(path(f"M {ox - 1} {back_y} L {loop_x + 8} {back_y} Q {loop_x} {back_y} {loop_x} {back_y - 8} "
                     f"L {loop_x} {fy + fh + 3}", GREEN, 1.3, dash="5,4", marker="arrGreen"))
    flow.append(rect(loop_x + 60, back_y - 22, 196, 14, WHITE, None, rx=2))
    flow.append(text(loop_x + 158, back_y - 11, ["verdicts become labels that retrain agents"], 10.5, GREEN, "bold", anchor="middle"))
    content.append(group("method-flow", (450, fy - 4, 800, oy + 48 - fy + 4), *flow))

    # -- working prototype
    py = oy + 62
    img_h = 660 - py
    img_w = round(img_h * 755 / 695)
    proto = [rect(rx0, py, img_w, img_h, WHITE, RULE, rx=4),
             f'<image href="../images/live_prototype.png" x="{rx0 + 1}" y="{py + 1}" width="{img_w - 2}" '
             f'height="{img_h - 2}" preserveAspectRatio="xMidYMid meet"/>']
    content.append(group("prototype-shot", (rx0, py, img_w, img_h), *proto))
    tx = rx0 + img_w + 18
    tw = 1248 - tx
    facts, _ = bullet_list(tx, py + 44, [
        "All 2,09,993 real works assessed; 276 (0.13%) sit in the review queue.",
        "Live today: Cost agent, Data Validation, Risk Fusion, India map on official LGD outlines.",
        "Tried offline on 837 real completed works and their 905 downloaded files.",
        "Code and full trial write-up: github.com/AdityaMore776/drishti",
    ], tw, 12.5, gap=6)
    cy0 = _ + 6
    card = [rect(tx, cy0, tw, 660 - cy0, PANEL, None, rx=6),
            text(tx + 12, cy0 + 20, ["EVERY AGENT ANSWERS IN THE SAME FORM"], 11, NAVY, "bold")]
    fields = [("status", "checked · not applicable · could not assess"), ("risk + confidence", "0–1 each"),
              ("headline", "one plain sentence for the officer"), ("evidence", "the photo, paper or number behind it"),
              ("limits", "what it could not check — always shown")]
    fy2 = cy0 + 40
    for k, v in fields:
        card.append(text(tx + 12, fy2, [[run(k, weight="bold", fill=INK), run("   " + v, fill=BODY)]], 12))
        fy2 += 17
    facts += card
    content.append(group("prototype-facts", (tx - 2, py, tw + 4, img_h),
                         text(tx, py + 14, ["WORKING PROTOTYPE — LIVE"], 11, GREEN, "bold"),
                         text(tx, py + 30, [[run("drishti-lyart.vercel.app", fill=BLUE, weight="bold"),
                                             run("  · sign-in by role", fill=MUTED, size=11.5)]], 13),
                         *facts))
    return finish(svg, content, ARROW_DEFS)


# ================================================================= SLIDE 4 — feasibility
COST_CHART = [("2×", 18), ("3×", 39), ("5×", 63), ("10×", 84)]


def cost_chart(x, y, w, h) -> str:
    """Native-ready column chart: share of inflated works the Cost agent caught."""
    import json
    plot_x, plot_y, plot_w, plot_h = x + 30, y + 30, w - 40, h - 74
    parts = [text(x, y + 12, ["Cost agent: inflated works caught"], 12.5, INK, "bold")]
    parts.append(f'<line id="cost-axis" x1="{plot_x}" y1="{plot_y + plot_h}" x2="{plot_x + plot_w}" '
                 f'y2="{plot_y + plot_h}" stroke="{MUTED}" stroke-width="1"/>')
    bw = plot_w / len(COST_CHART) * 0.56
    colors = []
    for i, (cat, v) in enumerate(COST_CHART):
        cx = plot_x + plot_w / len(COST_CHART) * (i + 0.5)
        bh = plot_h * v / 100
        fill = SAFFRON if cat == "5×" else NAVY
        colors.append(fill)
        parts.append(rect(cx - bw / 2, plot_y + plot_h - bh, bw, bh, fill, None, rx=0))
        parts.append(text(cx, plot_y + plot_h - bh - 5, [f"{v}%"], 12, INK, "bold", anchor="middle"))
        parts.append(text(cx, plot_y + plot_h + 15, [cat], 11.5, MUTED, anchor="middle"))
    notes = ["Mark-up applied to 1,000 real works.", "False alarms on 20,000 untouched works: 1.5%"]
    parts.append(text(x, y + h - 18, [notes[0]], 10.5, MUTED))
    parts.append(text(x, y + h - 5, [notes[1]], 10.5, MUTED))
    meta = {
        "x": x, "y": y, "width": w, "height": h, "name": "cost-chart", "type": "column",
        "title": "Cost agent: inflated works caught",
        "categories": [c for c, _ in COST_CHART],
        "series": [{"name": "Caught", "values": [v for _, v in COST_CHART], "point_colors": colors}],
        "data_labels": {"show_value": True, "number_format": '0"%"', "bold": True},
        "show_legend": False,
        "style": {"colors": [NAVY]},
        "notes": [{"text": n, "width": w} for n in notes],
    }
    return parts, meta


def slide4() -> str:
    svg = load(4)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-17410")
    content = []

    lx, lw = 32, 744
    p, b = pointer(lx, 142, "Analysis of the feasibility of the idea", lw)
    rows = [
        ("Cost", "1,000 real works inflated; 20,000 untouched", "Catches 63% of 5× mark-ups (84% of 10×); 1.5% false alarms", "live"),
        ("Photo Forensics", "319 real site photos, each edited 6 ways", "Recognises 99.9% of edited copies", "tested"),
        ("Geo-Location", "GPS stamps on 190 photos / pages, 170 works", "Coordinates right on all 12 checked by eye", "tested"),
        ("Document", "431 Uttar Pradesh utilisation certificates", "Amounts and payment dates read on ≥99%", "tested"),
        ("Eligibility", "Fresh sample of 50 flagged works", "56% plainly prohibited; 80% worth an officer's look", "tested"),
        ("Split works", "All 2,09,993 works", "12× more works just under ₹5 lakh than just over", "tested"),
        ("Delay", "Trained to Jan 2025; tested Jan–May 2025", "Ranking score 0.71 vs 0.68 for office record alone", "weak"),
        ("Satellite", "170 works with coordinates", "Median work ₹2.8 lakh — too small for 10 m pixels", "off"),
        ("Citizen", "eSAKSHI citizen ratings", "21,789 of 21,793 ratings are zero", "demo"),
    ]
    cx = [lx, lx + 112, lx + 350, lx + 688]
    hy = b + 8
    tab = [rect(lx, hy, lw, 22, NAVY, None, rx=0)]
    for x, h in zip(cx, ["Agent", "How we tested it on real eSAKSHI data", "Result", "Status"]):
        tab.append(text(x + 8, hy + 15, [h], 11.5, WHITE, "bold"))
    ry = hy + 22
    for i, (a, how, res, st) in enumerate(rows):
        rh = 25
        if i % 2 == 1:
            tab.append(rect(lx, ry, lw, rh, PANEL, None, rx=0))
        tab.append(text(cx[0] + 8, ry + 17, [a], 12, INK, "bold"))
        tab.append(text(cx[1] + 8, ry + 17, [how], 11.5, BODY))
        tab.append(text(cx[2] + 8, ry + 17, [res], 11.5, INK if st in ("live", "tested") else BODY,
                        "bold" if st in ("live", "tested") else None))
        tab.append(pill(cx[3] + 4, ry + 4.5, st))
        ry += rh
    tab.append(line(lx, ry, lx + lw, ry, RULE, 1))
    content.append(group("scorecard", (30, 124, 748, ry - 124 + 2), p, *tab))

    # chart + feasibility tiles
    by = ry + 14
    chart_parts, meta = cost_chart(lx, by, 330, 660 - by)
    content.append(group("cost-chart", (lx, by, 330, 660 - by), *chart_parts))   # editable shapes
    tiles = [("Technical", "Live prototype on Vercel + Supabase; every agent follows one reporting contract."),
             ("Data", "2,09,993 works loaded. 2 in 3 completed works carry certificates or photos."),
             ("Operational", "Read-only on eSAKSHI: no new data entry; fits the MP → District → Agency flow."),
             ("Economic", "Open-source stack and free text reading; paid AI only behind a capped switch.")]
    tx0, tw, th = lx + 350, (lw - 350 - 10) / 2, (660 - by - 10) / 2
    tparts = []
    for i, (t, d) in enumerate(tiles):
        x = tx0 + (i % 2) * (tw + 10)
        y = by + (i // 2) * (th + 10)
        tparts.append(rect(x, y, tw, th, WHITE, RULE, rx=6))
        tparts.append(rect(x, y, 4, th, NAVY, None, rx=0))
        tparts.append(text(x + 14, y + 22, [t + " feasibility"], 13, NAVY, "bold"))
        tparts.append(text(x + 14, y + 42, wrap(d, tw - 24, 12.5), 12.5, BODY, lh=16.5))
    content.append(group("feasibility-tiles", (tx0, by, lw - 350, 660 - by), *tparts))

    # challenges -> strategies (right)
    rx0, rw = 796, 452
    colw = 206
    h1, b1 = pointer(rx0, 142, "Potential challenges and risks", colw)
    h2, b2 = pointer(rx0 + colw + 40, 142, "Strategies for overcoming these challenges", colw)
    pairs = [
        ("No confirmed fraud labels", "Few proven cases to learn from.",
         "Planted test cases on real works; officers' verdicts become labels."),
        ("False alarms", "Bulk orders, terrain and rates can look like overpricing.",
         "Price alone can never make a work high-risk; separate agents must agree."),
        ("Hindi & handwritten papers", "51% of other states' PDFs can't be read locally.",
         "Unclear reading = “can't tell”, never an alert; AI reader behind a capped switch."),
        ("Personal data", "Phone and bank account numbers sit in public records.",
         "Masked before display; access scoped by role and district."),
        ("Portal habits look like misconduct", "e.g. bulk entry when eSAKSHI opened in 2023.",
         "Each office compared with the same period nationally."),
    ]
    top = max(b1, b2) + 10
    ph = (602 - top) / len(pairs)
    cparts = [h1, h2]
    for i, (t, d, s) in enumerate(pairs):
        y = top + i * ph
        cparts.append(rect(rx0, y, colw, ph - 8, PANEL, None, rx=6))
        tl = wrap(t, colw - 18, 12.5, True)
        cparts.append(text(rx0 + 10, y + 19, tl, 12.5, INK, "bold", lh=15))
        cparts.append(text(rx0 + 10, y + 21 + 15 * len(tl), wrap(d, colw - 18, 11.5), 11.5, MUTED, lh=14))
        cparts.append(line(rx0 + colw + 6, y + (ph - 8) / 2, rx0 + colw + 34, y + (ph - 8) / 2, NAVY, 1.4, marker="arrNavy"))
        sx = rx0 + colw + 40
        cparts.append(rect(sx, y, colw, ph - 8, WHITE, NAVY, rx=6, sw=1))
        cparts.append(text(sx + 10, y + 19, wrap(s, colw - 18, 12.5), 12.5, BODY, lh=16))
    content.append(group("challenges", (rx0 - 2, 124, rw + 4, 602 - 124), *cparts))

    proof = group("proof-before-launch", (rx0, 608, rw, 52),
                  rect(rx0, 608, rw, 52, NAVY, None, rx=6),
                  text(rx0 + 14, 624, ["PROOF BEFORE LAUNCH"], 12, SAFFRON, "bold"),
                  text(rx0 + 14, 640, wrap("An agent goes live only after it meets its accuracy target on real "
                                           "eSAKSHI works. If it fails, it stays switched off.", rw - 28, 11.5),
                       11.5, WHITE, lh=14))
    content.append(proof)
    return finish(svg, content, ARROW_DEFS)


# ================================================================= SLIDE 5 — impact
def slide5() -> str:
    svg = load(5)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-17410")
    content = []

    p, b = pointer(32, 142, "Potential impact on the target audience", 1216)
    groups = [
        ("Ministry (MoSPI)", ["National risk map by state and district",
                              "Sanction backlog and fund use, by Lok Sabha term",
                              "Each agent's accuracy tracked openly"]),
        ("State Nodal Authorities", ["District and agency track records",
                                     "Stuck or high-risk works to escalate",
                                     "Contractor concentration, from certificates"]),
        ("District Authorities", ["276 works to review instead of 2,09,993",
                                  "The 10% inspection plan, ranked by risk × money",
                                  "Eligibility and cost checks before sanction"]),
        ("MPs & citizens", ["Live status of recommended works",
                            "Early warning on stuck works",
                            "Citizens confirm completed assets (planned)"]),
    ]
    cw = (1216 - 3 * 12) / 4
    parts = [p]
    for i, (t, items) in enumerate(groups):
        x = 32 + i * (cw + 12)
        y0 = b + 10
        parts.append(rect(x, y0, cw, 124, PANEL, None, rx=6))
        parts.append(text(x + 14, y0 + 24, [t], 15, NAVY, "bold"))
        bl, _ = bullet_list(x + 14, y0 + 50, items, cw - 26, 13, gap=5)
        parts += bl
    content.append(group("stakeholders", (30, 124, 1220, b + 136 - 124), *parts))

    # already found
    fy = b + 158
    found = [
        ("21,323", "works (₹1,361 cr) waiting for sanction past the 75-day limit"),
        ("40,489", "works (₹2,178 cr) recommended Apr 2023–May 2024, still not complete two years on"),
        ("136", "groups of bulk orders (744 works) kept just under ₹5 lakh each"),
        ("282 / 285", "“completed” works whose certificate still says “in progress”"),
        ("3", "works whose own photos show them finished before the MP recommended them"),
    ]
    fparts = [text(32, fy, [[run("ALREADY FOUND IN REAL eSAKSHI DATA", weight="bold", fill=MUTED),
                             run("  — each one needs checking, none is a verdict", fill=MUTED)]], 11)]
    tw = (1216 - 4 * 10) / 5
    for i, (n, d) in enumerate(found):
        x = 32 + i * (tw + 10)
        y0 = fy + 10
        fparts.append(rect(x, y0, tw, 110, WHITE, RULE, rx=6))
        fparts.append(rect(x, y0, tw, 4, SAFFRON, None, rx=0))
        fparts.append(text(x + 12, y0 + 40, [n], 30, SAFF_TX, "bold"))
        fparts.append(text(x + 12, y0 + 62, wrap(d, tw - 22, 12.5), 12.5, BODY, lh=15.5))
    content.append(group("already-found", (30, fy - 14, 1220, 136), *fparts))

    # benefits + next steps
    by = fy + 150
    p2, b2 = pointer(32, by, "Benefits of the solution (social, economic, environmental, etc.)", 780)
    ben = [("SOCIAL", ["Assets exist where they are claimed", "Forbidden works caught before sanction", "Public trust through open records"]),
           ("ECONOMIC", ["Risk flagged before money moves", "Split works, repeats, padded costs caught", "Officer visits go where risk is highest"]),
           ("ENVIRONMENTAL", ["Remote checks from photos & GPS stamps", "Fewer wasted site trips and fuel", "Paperless, searchable records"])]
    bw = (780 - 2 * 12) / 3
    bparts = [p2]
    for i, (t, items) in enumerate(ben):
        x = 32 + i * (bw + 12)
        bparts.append(text(x, b2 + 20, [t], 12, GREEN, "bold"))
        bl, _ = bullet_list(x, b2 + 39, items, bw, 13, gap=3, marker=GREEN)
        bparts += bl
    content.append(group("benefits", (30, by - 18, 784, 588 - by + 18), *bparts))

    nx, nw = 836, 412
    p3, b3 = pointer(nx, by, "Next steps", nw)
    steps = [("✓", "Live prototype + trial on 837 real works", True),
             ("M1", "Document + Contractor agents", False),
             ("M2", "Eligibility v2, splits and repeats", False),
             ("M3", "Photo Forensics + Geo-Location", False),
             ("M4–M6", "AI reader, field app, Inspection Planner", False)]
    sparts = [p3]
    sy = b3 + 18
    for tag, s, done in steps:
        fill = GREEN if done else NAVY
        sparts.append(rect(nx, sy - 13, 50, 17, fill, None, rx=8.5))
        sparts.append(text(nx + 25, sy, [tag], 10.5, WHITE, "bold", anchor="middle"))
        sparts.append(text(nx + 60, sy, [s], 13, INK if done else BODY, "bold" if done else None))
        sy += 21
    content.append(group("next-steps", (nx - 2, by - 18, nw + 4, 588 - by + 18), *sparts))

    strip = group("takeaway", (32, 598, 1216, 60),
                  rect(32, 598, 1216, 60, NAVY, None, rx=6),
                  text(52, 636, [[run("2,09,993 works", fill=WHITE, weight="bold"),
                                  run("   →   ", fill=SAFFRON, weight="bold"),
                                  run("276 to check first", fill=SAFFRON, weight="bold")]], 22),
                  text(520, 624, ["Officers' time goes where the evidence is: 0.13% of works, each with its"], 13, WHITE),
                  text(520, 643, ["reasons, the guideline clause, and what DRISHTI could not check."], 13, WHITE))
    content.append(strip)
    return finish(svg, content, ARROW_DEFS)


# ================================================================= SLIDE 6 — references
def slide6() -> str:
    svg = load(6)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-17410")
    content = []

    lx, lw = 32, 548
    p, b = pointer(lx, 142, "Details / Links of the reference and research work", lw)
    refs = [
        ("GOVERNMENT & SCHEME SOURCES", [
            ("MoSPI — Guidelines on MPLADS (June 2016), paras 2.1, 3.12, 3.13, 3.22, 4.4, 6.4",
             "cdnbbsr.s3waas.gov.in/s3c3614206a443012045cfd75d2600af2d/uploads/2023/02/2023020891.pdf"),
            ("PIB — Revised MPLADS Guidelines 2023 (release 2155040, 11 Aug 2025)",
             "pib.gov.in/PressReleasePage.aspx?PRID=2155040"),
            ("CAG — Report No. 31 of 2010-11, Performance Audit of MPLADS (Annex 4.7, 7.2)",
             "cag.gov.in/uploads/download_audit_report/2010/Union_Performance_Local_area_Development_Scheme_31_2010_annexures.pdf"),
            ("MoSPI — eSAKSHI public dashboard and uploaded files (data to 26 May 2026)",
             "mplads.mospi.gov.in"),
        ]),
        ("METHODS WE USE", [
            ("Rublee, Rabaud, Konolige, Bradski — ORB: an efficient alternative to SIFT or SURF. ICCV 2011", None),
            ("Fischler & Bolles — Random Sample Consensus (RANSAC). Comm. ACM 24(6), 1981", None),
            ("Zauner — Implementation and Benchmarking of Perceptual Image Hash Functions. MSc thesis, 2010", None),
            ("Ke et al. — LightGBM: a highly efficient gradient boosting decision tree. NeurIPS 2017", None),
            ("Wilson — Probable inference, the law of succession, and statistical inference. JASA 22(158), 1927", None),
        ]),
        ("DATA & TOOLS", [
            ("LGD district outlines (via github.com/yashveeeeeeer/india-geodata) · India Post PIN–district "
             "mapping · OpenCV · scikit-learn · RapidOCR · PyMuPDF", None),
        ]),
    ]
    y, parts = b + 20, [p]
    n = 1
    for head, items in refs:
        parts.append(text(lx, y, [head], 11.5, GREEN, "bold"))
        y += 18
        for t, url in items:
            tl = wrap(t, lw - 24, 12.5)
            num = [run(f"{n}", fill=NAVY, weight="bold")] if head != "DATA & TOOLS" else [run("•", fill=NAVY, weight="bold")]
            parts.append(text(lx, y, [num], 12.5))
            parts.append(text(lx + 18, y, tl, 12.5, INK, lh=15))
            y += 15 * len(tl)
            if url:
                ul = wrap(url, lw - 24, 10.5)
                parts.append(text(lx + 18, y, ul, 10.5, BLUE, lh=13))
                y += 13 * len(ul)
            y += 5
            if head != "DATA & TOOLS":
                n += 1
        y += 9
    content.append(group("references", (30, 124, lw + 4, y - 124), *parts))

    # project links
    ly = max(y + 4, 592)
    assert ly <= 592, f"references run into the links box: {ly}"
    links = group("project-links", (lx, ly, lw, 660 - ly),
                  rect(lx, ly, lw, 660 - ly, NAVY, None, rx=6),
                  text(lx + 14, ly + 20, ["OUR WORK — OPEN TO CHECK"], 11.5, SAFFRON, "bold"),
                  text(lx + 14, ly + 40, [[run("Code  ", fill="#B9C7D8", size=11.5), run("github.com/AdityaMore776/drishti", fill=WHITE, weight="bold")]], 13),
                  text(lx + 14, ly + 58, [[run("Live demo  ", fill="#B9C7D8", size=11.5), run("drishti-lyart.vercel.app", fill=WHITE, weight="bold")]], 13),
                  text(lx + 280, ly + 40, [[run("Every number:  ", fill="#B9C7D8", size=11.5)]], 11.5),
                  text(lx + 280, ly + 58, [[run("docs/trial/FINDINGS.md", fill=WHITE, weight="bold")]], 12))
    content.append(links)

    # comparison chart (the only comparison in the deck)
    cx0, cw = 604, 644
    cparts = [text(cx0, 142, ["How DRISHTI compares with existing monitoring"], 15, NAVY, "bold"),
              line(cx0, 149, cx0 + cw, 149, RULE, 1)]
    cols = [cx0, cx0 + 176, cx0 + 402]
    widths = [176, 226, 242]
    hy = 158
    cparts.append(rect(cx0, hy, cw, 26, NAVY, None, rx=0))
    for x, h in zip(cols, ["Capability", "Existing systems*", "DRISHTI"]):
        cparts.append(text(x + 8, hy + 17, [h], 12, WHITE, "bold"))
    rows = [
        ("Coverage", ("part", "Every work stored; audits check a sample"), ("yes", "Every work assessed — 2,09,993 today")),
        ("Cost vs similar works", ("part", "Manual review in audits"), ("yes", "Live: district cost bands for every work")),
        ("Reused or edited photos", ("no", "Photos viewed by eye"), ("yes", "99.9% of edited copies recognised")),
        ("Photo place & time", ("part", "Geotag shown on a map"), ("yes", "GPS stamp read; district and date checked")),
        ("Reads certificates & bills", ("no", "Stored as files"), ("yes", "Sanction date, payments, vendor read")),
        ("Split works & repeats", ("no", "Not automated"), ("part", "Splits found; reworded repeats next")),
        ("Risk-ranked review list", ("no", "Sample picked by hand"), ("yes", "276 works ranked by risk × money")),
        ("Explains each flag", ("no", "—"), ("yes", "Evidence + guideline clause, every flag")),
        ("Site progress from photos", ("no", "Checked by eye"), ("part", "Planned: AI vision, behind a switch")),
    ]
    mark = {"yes": ("YES", GREEN, WHITE, GREEN), "no": ("NO", WHITE, MUTED, MUTED),
            "part": ("PARTLY", WHITE, SAFF_TX, SAFFRON)}
    ry = hy + 26
    rh = 44
    for i, (cap, ex, dr) in enumerate(rows):
        if i % 2 == 1:
            cparts.append(rect(cx0, ry, cw, rh, PANEL, None, rx=0))
        cparts.append(text(cols[0] + 8, ry + 26, wrap(cap, widths[0] - 16, 12.5), 12.5, INK, "bold", lh=15))
        for x, w, (k, d) in ((cols[1], widths[1], ex), (cols[2], widths[2], dr)):
            lab, fill, tx, st = mark[k]
            pw = 50
            cparts.append(rect(x + 8, ry + 8, pw, 15, fill, st, rx=7.5, sw=1))
            cparts.append(text(x + 8 + pw / 2, ry + 19, [lab], 9, tx, "bold", anchor="middle"))
            cparts.append(text(x + 8, ry + 37, wrap(d, w - 16, 11.5)[:1], 11.5, BODY if k != "no" else MUTED))
        ry += rh
    cparts.append(line(cx0, ry, cx0 + cw, ry, RULE, 1))
    for x in cols[1:]:
        cparts.append(line(x, hy, x, ry, RULE, 1))
    cparts.append(text(cx0, ry + 16, ["*eSAKSHI, PMAY-G AwaasApp, GeoMGNREGA / NMMS, CAG and social audits — as described "
                                      "in their public documents."], 10, MUTED))
    content.append(group("comparison", (cx0 - 2, 124, cw + 4, ry + 22 - 124), *cparts))
    return finish(svg, content, ARROW_DEFS)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for n, fn in enumerate([slide1, slide2, slide3, slide4, slide5, slide6], start=1):
        (OUT / f"slide_{n:02d}.svg").write_text(fn(), encoding="utf-8")
        print(f"slide_{n:02d}.svg written")


if __name__ == "__main__":
    main()
