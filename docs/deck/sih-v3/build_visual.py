"""DRISHTI SIH 2026 deck, visual edition: slides 2-6 as diagrams, icons and short labels.

Reuses the helpers and the title slide from build_slides.py. Every number is in CONTENT_PLAN.md.
Icons: phosphor-duotone (one stylistic library) + simple-icons for real product logos,
synced into ./icons with ppt-master's icon_sync.py.

    python3 build_visual.py            # writes authoring-svg-flat/slide_01..06.svg
"""
from __future__ import annotations

from build_slides import (ARROW_DEFS, BLUE, BLUE_T, BODY, FONT, GREEN, GREEN_T, INK, MUTED, NAVY, OUT, PANEL,
                          RULE, SAFF_T, SAFF_TX, SAFFRON, WHITE, drop_group, finish, group, line, load, path,
                          pointer, r2, rect, run, set_team, slide1, sub_once, text, wrap)

RED = "#B42318"
RED_T = "#FDECEA"
GREY_T = "#EEF1F5"


# ---------------------------------------------------------------- visual primitives
def icon(name, x, y, s, fill=NAVY, lib="phosphor-duotone") -> str:
    return f'<use data-icon="{lib}/{name}" x="{r2(x)}" y="{r2(y)}" width="{r2(s)}" height="{r2(s)}" fill="{fill}"/>'


def badge(cx, cy, r, name, fg=NAVY, bg=BLUE_T, ring=None) -> str:
    ring_attr = f' stroke="{ring}" stroke-width="1.5"' if ring else ""
    s = r * 1.15
    return (f'<circle cx="{r2(cx)}" cy="{r2(cy)}" r="{r2(r)}" fill="{bg}"{ring_attr}/>'
            + icon(name, cx - s / 2, cy - s / 2, s, fg))


def arrow(x1, y1, x2, y2, color=NAVY, sw=1.6, dash=None) -> str:
    marker = {NAVY: "arrNavy", GREEN: "arrGreen", SAFFRON: "arrSaff"}.get(color, "arrMuted")
    return line(x1, y1, x2, y2, color, sw, dash=dash, marker=marker)


def chevron(x, y, w, h, fill, first=False) -> str:
    t = 12
    pts = ([(x, y), (x + w - t, y), (x + w, y + h / 2), (x + w - t, y + h), (x, y + h)] if first else
           [(x, y), (x + w - t, y), (x + w, y + h / 2), (x + w - t, y + h), (x, y + h), (x + t, y + h / 2)])
    return f'<polygon points="{" ".join(f"{r2(a)},{r2(b)}" for a, b in pts)}" fill="{fill}"/>'


def status_dot(cx, cy, kind) -> str:
    if kind == "live":
        return f'<circle cx="{r2(cx)}" cy="{r2(cy)}" r="4.5" fill="{GREEN}"/>'
    if kind == "tested":
        return f'<circle cx="{r2(cx)}" cy="{r2(cy)}" r="4.5" fill="{BLUE}"/>'
    return f'<circle cx="{r2(cx)}" cy="{r2(cy)}" r="4" fill="{WHITE}" stroke="{MUTED}" stroke-width="1.3"/>'


PILL = {"live": ("LIVE", GREEN, WHITE, GREEN), "tested": ("TESTED", BLUE, WHITE, BLUE),
        "weak": ("WEAK", WHITE, SAFF_TX, SAFFRON), "off": ("OFF", WHITE, MUTED, MUTED),
        "demo": ("DEMO ONLY", WHITE, MUTED, MUTED)}


def pill(x, y, kind, w=None, h=16) -> str:
    label, fill, tx, stroke = PILL[kind]
    w = w or (len(label) * 6.2 + 14)
    return (rect(x, y, w, h, fill, stroke, rx=h / 2, sw=1)
            + text(x + w / 2, y + h - 4.5, [label], 9.5, tx, "bold", anchor="middle"))


def small_head(x, y, label, color=MUTED, size=11) -> str:
    return text(x, y, [label], size, color, "bold")


# ================================================================= SLIDE 2 — the idea as one picture
def slide2() -> str:
    svg = load(2)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-15362")
    svg = sub_once(svg, '<tspan x="595.21" dy="57.6">IDEA TITLE</tspan>',
                   '<tspan x="595.21" dy="57.6"><tspan>DRISHTI</tspan><tspan font-size="24" font-weight="normal" '
                   'font-style="italic" fill="#344054">  ·  the AI-eye on every MPLADS rupee</tspan></tspan>')
    c = []

    p, b = pointer(32, 142, "Proposed Solution (Describe your Idea/Solution/Prototype)", 1216)
    lead = text(32, b + 20, [[run("A read-only AI layer on eSAKSHI. ", weight="bold", fill=INK),
                              run("Every work is checked; only the risky ones reach an officer, with the evidence.",
                                  fill=BODY)]], 15)
    c.append(group("solution", (30, 124, 1220, b + 26 - 124), p, lead))

    # ---- the pipeline: eSAKSHI -> 12 agents across the life of a work -> score -> list -> officer
    top = 204
    d = [small_head(32, top, "DETAILED EXPLANATION OF THE PROPOSED SOLUTION", NAVY, 11.5)]
    # source node
    d += [badge(86, 318, 36, "database", NAVY, PANEL, RULE),
          text(86, 372, ["eSAKSHI"], 14, INK, "bold", anchor="middle"),
          text(86, 388, ["works, papers,"], 11, MUTED, anchor="middle"),
          text(86, 402, ["site photos"], 11, MUTED, anchor="middle"),
          arrow(126, 318, 156, 318)]
    # lifecycle panel
    px, pw, py, ph = 162, 700, 216, 212
    d.append(rect(px, py, pw, ph, WHITE, RULE, rx=8))
    lanes = [
        ("Before sanction", [("prohibit", "Eligibility", "tested"), ("copy", "Duplicate & Split", "tested"),
                             ("currency-inr", "Cost", "live")]),
        ("During construction", [("hard-hat", "Site Progress", "planned"), ("image", "Photo Forensics", "tested"),
                                 ("map-pin", "Geo-Location", "tested"), ("file-text", "Document", "tested"),
                                 ("globe-hemisphere-east", "Satellite", "planned")]),
        ("Money & time", [("hourglass-medium", "Delay", "tested"), ("hand-coins", "Fund Flow", "tested"),
                          ("handshake", "Contractor", "tested")]),
        ("After completion", [("qr-code", "Citizen check", "planned")]),
    ]
    lw = (pw - 20) / 4
    for i, (name, agents) in enumerate(lanes):
        lx = px + 10 + i * lw
        d.append(chevron(lx, py + 10, lw - 2, 28, NAVY if i % 2 == 0 else "#1B5A94", first=(i == 0)))
        d.append(text(lx + lw / 2 + (0 if i == 0 else 4), py + 29, [name], 12, WHITE, "bold", anchor="middle"))
        ay = py + 50
        for ic, an, st in agents:
            d.append(rect(lx + 4, ay, lw - 14, 28, PANEL, None, rx=5))
            d.append(icon(ic, lx + 10, ay + 4, 20, NAVY))
            d.append(text(lx + 36, ay + 19, [an], 12.5, INK, "bold"))
            d.append(status_dot(lx + lw - 22, ay + 14, st))
            ay += 31.5
    capx = px + 10 + lw * 3
    d.append(text(capx, py + 170, ["12 AI AGENTS"], 13, NAVY, "bold", anchor="middle"))
    d.append(text(capx, py + 186, ["each answers one question"], 11, MUTED, anchor="middle"))
    d.append(text(capx, py + 200, ["about the work"], 11, MUTED, anchor="middle"))
    # outcome column
    ox = 900
    outs = [("gauge", "Risk score", "0–100, parts add up", SAFFRON, SAFF_T),
            ("list-numbers", "Ranked review list", "risk × money", NAVY, BLUE_T),
            ("user-check", "Officer decides", "visits, then gives a verdict", GREEN, GREEN_T)]
    d.append(arrow(px + pw + 2, 318, ox - 4, 318))
    oy = 222
    for i, (ic, t1, t2, fg, bg) in enumerate(outs):
        d.append(rect(ox, oy, 348, 58, bg, fg, rx=8, sw=1.2))
        d.append(badge(ox + 32, oy + 29, 20, ic, fg, WHITE))
        d.append(text(ox + 62, oy + 25, [t1], 15, INK, "bold"))
        d.append(text(ox + 62, oy + 43, [t2], 12, MUTED))
        if i < 2:
            d.append(arrow(ox + 174, oy + 58, ox + 174, oy + 74))
        oy += 76
    # feedback loop: officer verdicts -> agents
    d.append(path(f"M {ox + 348 - 30} {oy - 18} L {ox + 348 - 30} 446 L {px + pw / 2} 446 L {px + pw / 2} {py + ph + 4}",
                  GREEN, 1.4, dash="5,4", marker="arrGreen"))
    d.append(text(ox + 73, 463, ["verdicts become training labels (next)"], 11, GREEN, "bold", anchor="middle"))
    # legend
    d += [status_dot(40, 470, "live"), text(49, 474, ["live"], 11, MUTED),
          status_dot(84, 470, "tested"), text(93, 474, ["tested on real eSAKSHI works"], 11, MUTED),
          status_dot(262, 470, "planned"), text(271, 474, ["planned"], 11, MUTED)]
    c.append(group("pipeline", (30, top - 14, 1220, 478 - (top - 14)), *d))

    # ---- how it addresses the problem: problem -> fix
    y0 = 506
    h1, hb = pointer(32, y0, "How it addresses the problem", 600)
    rows = [("signpost", "4,918", "works had no plaque (CAG)", "image", "Photo + plaque check"),
            ("hourglass-medium", "12,006", "works left incomplete (CAG)", "clock", "Stuck-work alerts"),
            ("magnifying-glass", "10%", "of works a district must inspect", "sort-descending", "Risk-ranked visit list")]
    pr = [h1]
    ry = hb + 12
    for ic, num, what, fic, fix in rows:
        pr.append(badge(52, ry + 20, 18, ic, RED, RED_T))
        pr.append(text(78, ry + 18, [num], 18, RED, "bold"))
        pr.append(text(78, ry + 33, [what], 11.5, MUTED))
        pr.append(arrow(292, ry + 20, 346, ry + 20))
        pr.append(badge(372, ry + 20, 18, fic, GREEN, GREEN_T))
        pr.append(text(398, ry + 25, [fix], 14, INK, "bold"))
        ry += 46
    c.append(group("problem-fix", (30, y0 - 18, 606, 660 - (y0 - 18)), *pr))

    # ---- innovation: 4 icon tiles
    h2, hb2 = pointer(660, y0, "Innovation and uniqueness of the solution", 588)
    tiles = [("map-pin", "Reads the GPS stamp", "printed inside site photos"),
             ("flask", "Proven before launch", "on real eSAKSHI works"),
             ("seal-check", "Evidence, not accusation", "every flag cites its clause"),
             ("file-text", "Reads papers for free", "certificates & bills, on our server")]
    it = [h2]
    tw, th = 289, 62
    for i, (ic, t1, t2) in enumerate(tiles):
        x = 660 + (i % 2) * (tw + 10)
        y = hb2 + 12 + (i // 2) * (th + 10)
        it.append(rect(x, y, tw, th, PANEL, None, rx=8))
        it.append(badge(x + 30, y + th / 2, 20, ic, SAFF_TX, WHITE))
        it.append(text(x + 60, y + 27, [t1], 14, INK, "bold"))
        it.append(text(x + 60, y + 45, [t2], 12, MUTED))
    c.append(group("innovation", (658, y0 - 18, 592, 660 - (y0 - 18)), *it))
    return finish(svg, c, ARROW_DEFS)


# ================================================================= SLIDE 3 — stack + flow + live prototype
def slide3() -> str:
    svg = load(3)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-17410")
    c = []

    # ---- technology layer stack
    lx, lw = 32, 398
    p, b = pointer(lx, 142, "Technologies to be used (e.g. programming languages, frameworks, hardware)", lw)
    layers = [
        ("Screens", "web dashboards", [("nextdotjs", "Next.js"), ("react", "React"), ("tailwindcss", "Tailwind"),
                                       ("maplibre", "MapLibre")]),
        ("Engine", "API + agents", [("python", "Python"), ("fastapi", "FastAPI")]),
        ("Data", "Mumbai region", [("postgresql", "PostgreSQL"), ("supabase", "Supabase")]),
        ("AI & vision", "+ LightGBM, OCR", [("scikitlearn", "scikit-learn"), ("opencv", "OpenCV"), ("pandas", "pandas"),
                                            ("googlegemini", "Gemini*")]),
        ("Hosting", "tests on every push", [("vercel", "Vercel"), ("githubactions", "Actions"), ("github", "GitHub")]),
    ]
    st = [p]
    y = b + 12
    bh = 80
    for i, (name, sub, logos) in enumerate(layers):
        st.append(rect(lx, y, lw, bh - 6, PANEL if i % 2 == 0 else WHITE, RULE, rx=6))
        st.append(rect(lx, y, 5, bh - 6, NAVY, None, rx=0))
        st.append(text(lx + 16, y + 32, [name], 14, NAVY, "bold"))
        st.append(text(lx + 16, y + 50, [sub], 10.5, MUTED))
        for j, (lg, lab) in enumerate(logos):
            cx = lx + 150 + j * 62
            st.append(icon(lg, cx - 14, y + 11, 28, INK, lib="simple-icons"))
            st.append(text(cx, y + 60, [lab], 10, BODY, anchor="middle"))
        y += bh
    st.append(badge(lx + 18, y + 22, 16, "device-mobile", GREEN, GREEN_T))
    st.append(text(lx + 42, y + 20, ["No hardware to buy"], 13.5, INK, "bold"))
    st.append(text(lx + 42, y + 36, ["officers use a browser or a phone · *Gemini planned"], 11, MUTED))
    c.append(group("tech-stack", (30, 124, lw + 4, y + 44 - 124), *st))

    # ---- methodology flow
    rx0, rw = 456, 792
    p2, b2 = pointer(rx0, 142, "Methodology and process for implementation (Flow Charts/Images/ working prototype)", rw)
    c.append(group("method-heading", (rx0 - 2, 124, rw + 4, b2 - 124 + 4), p2))
    nodes = [("database", "eSAKSHI", "2,09,993 works + files", NAVY, PANEL),
             ("shield-check", "Validate", "clean dates, mask IDs", NAVY, BLUE_T),
             ("eye", "12 agents", "4 stages of a work", NAVY, BLUE_T),
             ("gauge", "Risk Fusion", "one score, 0–100", SAFF_TX, SAFF_T),
             ("list-numbers", "Review queue", "ranked, with evidence", NAVY, BLUE_T)]
    cy = b2 + 56
    step = rw / 5
    f = []
    for i in range(4):
        x1 = rx0 + step * (i + 0.5) + 36
        f.append(arrow(x1, cy, rx0 + step * (i + 1.5) - 38, cy))
    for i, (ic, t1, t2, fg, bg) in enumerate(nodes):
        cx = rx0 + step * (i + 0.5)
        f.append(badge(cx, cy, 32, ic, fg, bg, fg))
        f.append(text(cx, cy + 52, [t1], 14, INK, "bold", anchor="middle"))
        f.append(text(cx, cy + 68, [t2], 11, MUTED, anchor="middle"))
    # officer + feedback loop
    ocx, ocy = rx0 + step * 4.5, cy + 118
    f.append(arrow(ocx, cy + 74, ocx, ocy - 24))
    f.append(badge(ocx, ocy, 22, "user-check", GREEN, GREEN_T, GREEN))
    f.append(text(ocx - 30, ocy + 5, ["Officer decides"], 13.5, INK, "bold", anchor="end"))
    agx = rx0 + step * 2.5
    f.append(path(f"M {ocx} {ocy + 22} L {ocx} {ocy + 34} L {agx} {ocy + 34} L {agx} {cy + 76}",
                  GREEN, 1.4, dash="5,4", marker="arrGreen"))
    f.append(text(agx + 14, ocy + 26, ["verdicts retrain the agents (next)"], 11, GREEN, "bold"))
    c.append(group("method-flow", (rx0 - 2, b2 + 14, rw + 4, ocy + 44 - (b2 + 14)), *f))

    # ---- working prototype: screenshot + three numbers
    py = ocy + 56
    ih = 660 - py
    iw = round(ih * 755 / 695)
    c.append(group("prototype-shot", (rx0, py, iw, ih),
                   rect(rx0, py, iw, ih, WHITE, RULE, rx=4),
                   f'<image href="../images/live_prototype.png" x="{rx0 + 1}" y="{py + 1}" width="{iw - 2}" '
                   f'height="{ih - 2}" preserveAspectRatio="xMidYMid meet"/>'))
    tx = rx0 + iw + 20
    tw = 1248 - tx
    pp = [small_head(tx, py + 12, "WORKING PROTOTYPE · LIVE", GREEN, 11.5),
          icon("globe-hemisphere-east", tx, py + 21, 18, BLUE),
          text(tx + 24, py + 35, ["drishti-lyart.vercel.app"], 14, BLUE, "bold")]
    stats = [("2,09,993", "real works assessed"), ("276", "in the review queue (0.13%)"),
             ("837", "real works tested with their files")]
    sw_ = (tw - 20) / 3
    for i, (n, lab) in enumerate(stats):
        x = tx + i * (sw_ + 10)
        pp.append(rect(x, py + 50, sw_, 74, PANEL, None, rx=6))
        pp.append(text(x + 10, py + 80, [n], 22, NAVY, "bold"))
        pp.append(text(x + 10, py + 99, wrap(lab, sw_ - 18, 11), 11, MUTED, lh=13))
    # every agent answers in one form: chips
    pp.append(small_head(tx, py + 146, "EVERY AGENT ANSWERS IN ONE FORM"))
    chips = ["status", "risk", "confidence", "evidence", "what it could not check"]
    cx_ = tx
    cyy = py + 156
    for ch in chips:
        w = len(ch) * 6.3 + 20
        if cx_ + w > 1248:
            cx_, cyy = tx, cyy + 28
        pp.append(rect(cx_, cyy, w, 22, BLUE_T, None, rx=11))
        pp.append(text(cx_ + w / 2, cyy + 15, [ch], 11.5, NAVY, "bold", anchor="middle"))
        cx_ += w + 8
    ry_ = cyy + 44
    pp.append(small_head(tx, ry_, "SIGN-IN BY ROLE"))
    roles = [("bank", "Ministry", "all India"), ("map-trifold", "District", "own district"),
             ("hard-hat", "Field", "site visits")]
    rw_ = (tw - 20) / 3
    for i, (ic, t1, t2) in enumerate(roles):
        x = tx + i * (rw_ + 10)
        pp.append(badge(x + 18, ry_ + 30, 17, ic, NAVY, BLUE_T))
        pp.append(text(x + 42, ry_ + 28, [t1], 13, INK, "bold"))
        pp.append(text(x + 42, ry_ + 43, [t2], 11, MUTED))
    c.append(group("prototype-facts", (tx - 2, py, tw + 4, ih), *pp))
    return finish(svg, c, ARROW_DEFS)


# ================================================================= SLIDE 4 — scorecard + risks + gate
def slide4() -> str:
    svg = load(4)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-17410")
    c = []

    lx, lw = 32, 744
    p, b = pointer(lx, 142, "Analysis of the feasibility of the idea", lw)
    tiles = [("currency-inr", "Cost", "live", "63%", "of 5× mark-ups caught · 1.5% false alarms"),
             ("image", "Photo Forensics", "tested", "99.9%", "of edited photo copies recognised"),
             ("map-pin", "Geo-Location", "tested", "12 / 12", "GPS points correct when checked"),
             ("file-text", "Document", "tested", "≥99%", "of amounts & payment dates read"),
             ("prohibit", "Eligibility", "tested", "56%", "of its flags plainly prohibited"),
             ("scissors", "Split works", "tested", "12×", "more works just under ₹5 lakh"),
             ("hourglass-medium", "Delay", "weak", "0.71", "vs 0.68 for the office's record"),
             ("globe-hemisphere-east", "Satellite", "off", "OFF", "pilot works too small to see"),
             ("qr-code", "Citizen", "demo", "4", "of 21,793 eSAKSHI ratings are above zero")]
    g = [p, small_head(lx, b + 20, "EACH AGENT, MEASURED ON REAL eSAKSHI WORKS")]
    tw, th, gap = (lw - 20) / 3, 90, 10
    for i, (ic, name, st, num, cap) in enumerate(tiles):
        x = lx + (i % 3) * (tw + gap)
        y = b + 30 + (i // 3) * (th + gap)
        good = st in ("live", "tested")
        g.append(rect(x, y, tw, th, WHITE, RULE, rx=8))
        g.append(badge(x + 24, y + 24, 16, ic, NAVY if good else MUTED, BLUE_T if good else GREY_T))
        g.append(text(x + 46, y + 29, [name], 13.5, INK, "bold"))
        g.append(pill(x + tw - (len(PILL[st][0]) * 6.2 + 14) - 10, y + 16, st))
        g.append(text(x + 14, y + 66, [num], 25, (GREEN if st == "live" else NAVY) if good else MUTED, "bold"))
        numw = len(num) * 14 + 14
        g.append(text(x + 14 + numw, y + 60, wrap(cap, tw - numw - 24, 11)[:2], 11, BODY, lh=13))
    gy = b + 30 + 3 * (th + gap)
    c.append(group("scorecard", (30, 124, lw + 4, gy - 124), *g))

    # mini chart + four feasibility icons
    ch = [small_head(lx, gy + 16, "COST AGENT: INFLATED WORKS CAUGHT")]
    base = 652
    bars = [("2×", 18), ("3×", 39), ("5×", 63), ("10×", 84)]
    for i, (k, v) in enumerate(bars):
        x = lx + 10 + i * 64
        hgt = (base - gy - 50) * v / 100
        ch.append(rect(x, base - 14 - hgt, 40, hgt, SAFFRON if k == "5×" else NAVY, None, rx=0))
        ch.append(text(x + 20, base - 18 - hgt, [f"{v}%"], 11.5, INK, "bold", anchor="middle"))
        ch.append(text(x + 20, base, [k], 11, MUTED, anchor="middle"))
    ch.append(line(lx, base - 14, lx + 262, base - 14, MUTED, 1))
    c.append(group("cost-chart", (lx, gy + 2, 270, 660 - gy - 2), *ch))
    feas = [("cloud", "Technical", "live on Vercel + Supabase"), ("database", "Data", "2 in 3 finished works have files"),
            ("users-three", "Operational", "read-only, no new data entry"), ("hand-coins", "Economic", "open source, AI cost capped")]
    fe = [small_head(lx + 290, gy + 16, "FEASIBILITY")]
    fw = (lw - 290 - 10) / 2
    for i, (ic, t1, t2) in enumerate(feas):
        x = lx + 290 + (i % 2) * (fw + 10)
        y = gy + 26 + (i // 2) * 58
        fe.append(rect(x, y, fw, 50, PANEL, None, rx=6))
        fe.append(badge(x + 24, y + 25, 16, ic, NAVY, WHITE))
        fe.append(text(x + 48, y + 22, [t1], 13, INK, "bold"))
        fe.append(text(x + 48, y + 38, [t2], 11, MUTED))
    c.append(group("feasibility", (lx + 288, gy + 2, lw - 286, 660 - gy - 2), *fe))

    # ---- challenges -> strategies
    rx0 = 796
    colw = 212
    h1, b1 = pointer(rx0, 142, "Potential challenges and risks", colw)
    h2, b2 = pointer(rx0 + colw + 28, 142, "Strategies for overcoming these challenges", colw)
    pairs = [("flag", "No confirmed fraud labels", "target", "Planted test cases; officer verdicts as labels"),
             ("warning", "False alarms", "check-square", "Price alone never makes a work high-risk"),
             ("translate", "Hindi & handwritten papers", "scan", "Unclear reads = “can't tell”; AI reader capped"),
             ("lock-key", "Personal data in records", "shield-check", "Phone & bank numbers masked; role access"),
             ("calendar-x", "Portal habits look odd", "chart-line-up", "Compare each office with the same period")]
    cp = [h1, h2]
    y = max(b1, b2) + 12
    rh = 60
    for ic, t, sic, s in pairs:
        cp.append(rect(rx0, y, colw, rh - 8, RED_T, None, rx=8))
        cp.append(icon(ic, rx0 + 10, y + 13, 26, RED))
        cp.append(text(rx0 + 44, y + 21, wrap(t, colw - 52, 12.5, True), 12.5, INK, "bold", lh=15))
        cp.append(arrow(rx0 + colw + 3, y + (rh - 8) / 2, rx0 + colw + 25, y + (rh - 8) / 2))
        sx = rx0 + colw + 28
        cp.append(rect(sx, y, colw, rh - 8, GREEN_T, None, rx=8))
        cp.append(icon(sic, sx + 10, y + 13, 26, GREEN))
        cp.append(text(sx + 44, y + 21, wrap(s, colw - 52, 11.5), 11.5, BODY, lh=14))
        y += rh
    c.append(group("challenges", (rx0 - 2, 124, 454, y - 124), *cp))

    # ---- proof-before-launch gate
    gy0 = y + 6
    gp = [rect(rx0, gy0, 452, 660 - gy0, NAVY, None, rx=8),
          small_head(rx0 + 14, gy0 + 20, "PROOF BEFORE LAUNCH", SAFFRON, 11.5)]
    my = gy0 + (660 - gy0) / 2 + 10
    gp.append(rect(rx0 + 14, my - 18, 118, 36, WHITE, None, rx=6))
    gp.append(icon("flask", rx0 + 20, my - 11, 22, NAVY))
    gp.append(text(rx0 + 46, my - 2, ["Test on real"], 11.5, INK, "bold"))
    gp.append(text(rx0 + 46, my + 11, ["eSAKSHI works"], 11.5, INK, "bold"))
    gp.append(arrow(rx0 + 134, my, rx0 + 160, my, SAFFRON))
    dx = rx0 + 212
    gp.append(f'<polygon points="{dx},{r2(my - 26)} {dx + 50},{r2(my)} {dx},{r2(my + 26)} {dx - 50},{r2(my)}" fill="{SAFFRON}"/>')
    gp.append(text(dx, my - 2, ["Meets its"], 11, WHITE, "bold", anchor="middle"))
    gp.append(text(dx, my + 11, ["target?"], 11, WHITE, "bold", anchor="middle"))
    yx = rx0 + 300
    gp.append(path(f"M {dx + 50} {r2(my)} L {dx + 62} {r2(my)} L {dx + 62} {r2(my - 20)} L {yx - 3} {r2(my - 20)}", SAFFRON, 1.5, marker="arrSaff"))
    gp.append(path(f"M {dx + 62} {r2(my)} L {dx + 62} {r2(my + 20)} L {yx - 3} {r2(my + 20)}", SAFFRON, 1.5, marker="arrSaff"))
    gp.append(rect(yx, my - 34, 138, 28, GREEN_T, None, rx=6))
    gp.append(icon("check-circle", yx + 6, my - 30, 20, GREEN))
    gp.append(text(yx + 32, my - 15, ["yes → goes live"], 12, INK, "bold"))
    gp.append(rect(yx, my + 6, 138, 28, GREY_T, None, rx=6))
    gp.append(icon("x-circle", yx + 6, my + 10, 20, MUTED))
    gp.append(text(yx + 32, my + 25, ["no → stays off"], 12, INK, "bold"))
    c.append(group("proof-gate", (rx0, gy0, 452, 660 - gy0), *gp))
    return finish(svg, c, ARROW_DEFS)


# ================================================================= SLIDE 5 — who gains, what's found, what's next
def slide5() -> str:
    svg = load(5)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-17410")
    c = []

    # ---- stakeholders
    p, b = pointer(32, 142, "Potential impact on the target audience", 780)
    who = [("bank", "Ministry", ["national risk map", "sanction backlog"]),
           ("buildings", "State nodal", ["district track records", "what to escalate"]),
           ("map-trifold", "District", ["276 works to review", "10% inspection plan"]),
           ("users-three", "MPs & citizens", ["live work status", "stuck-work warnings"])]
    s = [p]
    cw = (780 - 3 * 12) / 4
    for i, (ic, name, pts) in enumerate(who):
        x = 32 + i * (cw + 12)
        y = b + 12
        s.append(rect(x, y, cw, 172, PANEL, None, rx=8))
        s.append(badge(x + cw / 2, y + 44, 30, ic, NAVY, WHITE))
        s.append(text(x + cw / 2, y + 100, [name], 16, INK, "bold", anchor="middle"))
        s.append(text(x + cw / 2, y + 124, pts, 12.5, BODY, lh=18, anchor="middle"))
    c.append(group("stakeholders", (30, 124, 784, b + 186 - 124), *s))

    # ---- funnel: 2,09,993 -> 276
    fx, fw = 836, 412
    fu = [small_head(fx, 142, "FROM EVERY WORK TO THE FEW THAT MATTER", NAVY, 11.5)]
    levels = [("2,09,993", "works in eSAKSHI", NAVY, WHITE, 412),
              ("12 agents", "check every one", "#1B5A94", WHITE, 330),
              ("276", "to review first · 0.13%", SAFFRON, WHITE, 248)]
    y = 154
    lh_ = 50
    for i, (n, lab, fill, tx, w) in enumerate(levels):
        nw = levels[i + 1][4] if i + 1 < len(levels) else w - 40
        x0 = fx + (fw - w) / 2
        x1 = fx + (fw - nw) / 2
        fu.append(f'<polygon points="{r2(x0)},{r2(y)} {r2(x0 + w)},{r2(y)} {r2(x1 + nw)},{r2(y + lh_)} {r2(x1)},{r2(y + lh_)}" fill="{fill}"/>')
        fu.append(text(fx + fw / 2, y + 29, [[run(n + "  ", weight="bold", size=18), run(lab, size=12.5)]], 18, tx,
                       anchor="middle"))
        y += lh_ + 4
    fu.append(arrow(fx + fw / 2, y, fx + fw / 2, y + 12, SAFFRON))
    fu.append(text(fx + fw / 2, y + 28, ["→ the district's 10% inspection plan"], 12.5, SAFF_TX, "bold", anchor="middle"))
    c.append(group("funnel", (fx - 2, 124, fw + 4, y + 36 - 124), *fu))

    # ---- already found
    fy = b + 216
    found = [("hourglass-medium", "21,323", "works waiting for sanction past 75 days"),
             ("calendar-x", "40,489", "works still incomplete after two years"),
             ("scissors", "136", "bulk orders kept just under ₹5 lakh"),
             ("file-text", "282 / 285", "“done” works whose papers say “in progress”"),
             ("map-pin", "3", "works photographed finished before recommended")]
    fd = [text(32, fy, [[run("ALREADY FOUND IN REAL eSAKSHI DATA", weight="bold", fill=NAVY),
                         run("  ·  each one needs checking, none is a verdict", fill=MUTED)]], 11.5)]
    tw = (1216 - 4 * 10) / 5
    for i, (ic, n, lab) in enumerate(found):
        x = 32 + i * (tw + 10)
        y = fy + 10
        fd.append(rect(x, y, tw, 84, WHITE, RULE, rx=8))
        fd.append(rect(x, y + 10, 4, 64, SAFFRON, None, rx=0))
        fd.append(icon(ic, x + 14, y + 12, 26, SAFF_TX))
        fd.append(text(x + 48, y + 34, [n], 24, SAFF_TX, "bold"))
        fd.append(text(x + 14, y + 58, wrap(lab, tw - 24, 11.5)[:2], 11.5, BODY, lh=14))
    c.append(group("already-found", (30, fy - 14, 1220, 110), *fd))

    # ---- benefits
    by = fy + 138
    p2, b2 = pointer(32, by, "Benefits of the solution (social, economic, environmental, etc.)", 640)
    ben = [("users", "Social", ["assets exist where claimed", "trust through open records"], NAVY),
           ("currency-inr", "Economic", ["risk caught before money moves", "visits go where risk is"], SAFF_TX),
           ("leaf", "Environmental", ["remote checks from photos", "fewer wasted site trips"], GREEN)]
    bb = [p2]
    bw = (640 - 2 * 12) / 3
    for i, (ic, t, pts, col) in enumerate(ben):
        x = 32 + i * (bw + 12)
        bb.append(badge(x + 26, b2 + 38, 24, ic, col, PANEL))
        bb.append(text(x + 60, b2 + 44, [t], 15, col, "bold"))
        bb.append(text(x + 4, b2 + 86, pts, 13, BODY, lh=19))
    c.append(group("benefits", (30, by - 18, 644, 660 - by + 18), *bb))

    # ---- next steps timeline
    nx, nw = 696, 552
    p3, b3 = pointer(nx, by, "Next steps", nw)
    steps = [("✓", "Prototype live", "+ 837-work trial", True), ("M1", "Document +", "Contractor", False),
             ("M2", "Eligibility,", "splits, repeats", False), ("M3", "Photo +", "Geo checks", False),
             ("M4–6", "AI reader,", "field app", False)]
    tl = [p3]
    ty = b3 + 40
    x0, x1 = nx + 40, nx + nw - 40
    tl.append(line(x0, ty, x1, ty, RULE, 3))
    tl.append(line(x0, ty, x0 + (x1 - x0) / 8, ty, GREEN, 3))
    for i, (tag, l1, l2, done) in enumerate(steps):
        cx = x0 + i * (x1 - x0) / 4
        tl.append(f'<circle cx="{r2(cx)}" cy="{ty}" r="17" fill="{GREEN if done else NAVY}"/>')
        tl.append(text(cx, ty + 4.5, [tag], 11 if len(tag) > 2 else 13, WHITE, "bold", anchor="middle"))
        tl.append(text(cx, ty + 42, [l1], 12.5, INK, "bold", anchor="middle"))
        tl.append(text(cx, ty + 59, [l2], 12, MUTED, anchor="middle"))
    c.append(group("next-steps", (nx - 2, by - 18, nw + 4, 660 - by + 18), *tl))
    return finish(svg, c, ARROW_DEFS)


# ================================================================= SLIDE 6 — references + the one comparison
def slide6() -> str:
    svg = load(6)
    svg = set_team(svg)
    svg = drop_group(svg, "shape-17410")
    c = []

    lx, lw = 32, 548
    p, b = pointer(lx, 142, "Details / Links of the reference and research work", lw)
    refs = [
        ("bank", "GOVERNMENT & SCHEME SOURCES", [
            ("MoSPI — Guidelines on MPLADS (June 2016), paras 2.1, 3.12, 3.13, 3.22, 4.4, 6.4",
             "cdnbbsr.s3waas.gov.in/s3c3614206a443012045cfd75d2600af2d/uploads/2023/02/2023020891.pdf"),
            ("PIB — Revised MPLADS Guidelines 2023 (release 2155040, 11 Aug 2025)",
             "pib.gov.in/PressReleasePage.aspx?PRID=2155040"),
            ("CAG — Report No. 31 of 2010-11, Performance Audit of MPLADS (Annex 4.7, 7.2)",
             "cag.gov.in/uploads/download_audit_report/2010/Union_Performance_Local_area_Development_Scheme_31_2010_annexures.pdf"),
            ("MoSPI — eSAKSHI public dashboard and uploaded files (data to 26 May 2026)", "mplads.mospi.gov.in"),
        ]),
        ("flask", "METHODS WE USE", [
            ("Rublee et al. — ORB: an efficient alternative to SIFT or SURF. ICCV 2011", None),
            ("Fischler & Bolles — Random Sample Consensus (RANSAC). Comm. ACM 24(6), 1981", None),
            ("Zauner — Implementation and Benchmarking of Perceptual Image Hash Functions. MSc thesis, 2010", None),
            ("Ke et al. — LightGBM: a highly efficient gradient boosting decision tree. NeurIPS 2017", None),
            ("Wilson — Probable inference, the law of succession, and statistical inference. JASA 22(158), 1927", None),
        ]),
        ("map-trifold", "DATA & TOOLS", [
            ("LGD district outlines (github.com/yashveeeeeeer/india-geodata) · India Post PIN–district "
             "mapping · OpenCV · scikit-learn · RapidOCR · PyMuPDF", None),
        ]),
    ]
    y, parts, n = b + 22, [p], 1
    for ic, head, items in refs:
        parts.append(icon(ic, lx, y - 13, 16, GREEN))
        parts.append(text(lx + 22, y, [head], 11.5, GREEN, "bold"))
        y += 18
        for t, url in items:
            tl = wrap(t, lw - 24, 12)
            num = run(str(n), fill=NAVY, weight="bold") if head != "DATA & TOOLS" else run("•", fill=NAVY, weight="bold")
            parts.append(text(lx, y, [[num]], 12))
            parts.append(text(lx + 18, y, tl, 12, INK, lh=14.5))
            y += 14.5 * len(tl)
            if url:
                ul = wrap(url, lw - 24, 10.5)
                parts.append(text(lx + 18, y, ul, 10.5, BLUE, lh=13))
                y += 13 * len(ul)
            y += 5
            if head != "DATA & TOOLS":
                n += 1
        y += 8
    c.append(group("references", (30, 124, lw + 4, y - 124), *parts))
    ly = 594
    assert y <= ly, y
    c.append(group("project-links", (lx, ly, lw, 660 - ly),
                   rect(lx, ly, lw, 660 - ly, NAVY, None, rx=8),
                   icon("github", lx + 16, ly + 14, 22, WHITE, lib="simple-icons"),
                   text(lx + 46, ly + 24, ["Code"], 11, "#B9C7D8"),
                   text(lx + 46, ly + 40, ["github.com/AdityaMore776/drishti"], 13, WHITE, "bold"),
                   icon("globe-hemisphere-east", lx + 290, ly + 14, 22, WHITE),
                   text(lx + 320, ly + 24, ["Live demo"], 11, "#B9C7D8"),
                   text(lx + 320, ly + 40, ["drishti-lyart.vercel.app"], 13, WHITE, "bold"),
                   text(lx + 16, ly + 58, ["Every number on these slides: docs/trial/FINDINGS.md in the repo"], 10.5,
                        "#B9C7D8")))

    # ---- comparison chart
    cx0, cw = 604, 644
    cp = [text(cx0, 142, ["How DRISHTI compares with existing monitoring"], 15, NAVY, "bold"),
          line(cx0, 149, cx0 + cw, 149, RULE, 1)]
    cols, widths = [cx0, cx0 + 196, cx0 + 420], [196, 224, 224]
    hy = 158
    cp.append(rect(cx0, hy, cw, 28, NAVY, None, rx=0))
    for x, h in zip(cols, ["Capability", "Existing systems*", "DRISHTI"]):
        cp.append(text(x + 10, hy + 19, [h], 12.5, WHITE, "bold"))
    rows = [("users-three", "Coverage", ("part", "audits check a sample"), ("yes", "every work, 2,09,993")),
            ("currency-inr", "Cost vs similar works", ("part", "manual, in audits"), ("yes", "live, every work")),
            ("image", "Reused / edited photos", ("no", "viewed by eye"), ("yes", "99.9% recognised")),
            ("map-pin", "Photo place & time", ("part", "geotag on a map"), ("yes", "stamp read + checked")),
            ("file-text", "Reads certificates & bills", ("no", "stored as files"), ("yes", "dates, payments, vendor")),
            ("scissors", "Split works & repeats", ("no", "not automated"), ("part", "splits yes; rewording next")),
            ("list-numbers", "Risk-ranked review list", ("no", "picked by hand"), ("yes", "276, by risk × money")),
            ("seal-check", "Reason for each flag", ("no", "—"), ("yes", "evidence + clause")),
            ("hard-hat", "Progress from photos", ("no", "checked by eye"), ("part", "planned, AI vision"))]
    mark = {"yes": ("check-circle", GREEN), "no": ("x-circle", "#98A2B3"), "part": ("minus-circle", SAFFRON)}
    ry, rh = hy + 28, 45
    for i, (ic, cap, ex, dr) in enumerate(rows):
        if i % 2 == 1:
            cp.append(rect(cx0, ry, cw, rh, PANEL, None, rx=0))
        cp.append(icon(ic, cols[0] + 8, ry + 12, 20, NAVY))
        cp.append(text(cols[0] + 34, ry + 27, wrap(cap, widths[0] - 42, 12.5, True)[:1], 12.5, INK, "bold"))
        for x, (k, d) in ((cols[1], ex), (cols[2], dr)):
            mi, col = mark[k]
            cp.append(icon(mi, x + 10, ry + 11, 22, col))
            cp.append(text(x + 40, ry + 27, [d], 12, BODY if k != "no" else MUTED))
        ry += rh
    cp.append(line(cx0, ry, cx0 + cw, ry, RULE, 1))
    for x in cols[1:]:
        cp.append(line(x, hy, x, ry, RULE, 1))
    lg = ry + 18
    cp += [icon("check-circle", cx0, lg - 11, 14, GREEN), text(cx0 + 18, lg, ["yes"], 10.5, MUTED),
           icon("minus-circle", cx0 + 50, lg - 11, 14, SAFFRON), text(cx0 + 68, lg, ["partly"], 10.5, MUTED),
           icon("x-circle", cx0 + 114, lg - 11, 14, "#98A2B3"), text(cx0 + 132, lg, ["no"], 10.5, MUTED),
           text(cx0 + 170, lg, ["*eSAKSHI, PMAY-G AwaasApp, GeoMGNREGA / NMMS, CAG & social audits,"], 10, MUTED),
           text(cx0 + 170, lg + 12, ["as their own public documents describe them"], 10, MUTED)]
    c.append(group("comparison", (cx0 - 2, 124, cw + 4, lg + 18 - 124), *cp))
    return finish(svg, c, ARROW_DEFS)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for n, fn in enumerate([slide1, slide2, slide3, slide4, slide5, slide6], start=1):
        (OUT / f"slide_{n:02d}.svg").write_text(fn(), encoding="utf-8")
        print(f"slide_{n:02d}.svg written")


if __name__ == "__main__":
    main()
