"""Reading a site video once, offline (plan T120 §9.4; task T124).

The site video job (data/build_site_visits.py) uses this package to turn one uploaded video and
its capture log into the readings Site Progress judges (agents/site_progress/visits.py). It needs
OpenCV and NumPy (data/requirements-video.txt), which the live engine does not carry: nothing in
the engine imports this package.

    reader.py   frames, fingerprints, matching points, change at the same view, motion, faces
    visit.py    one visit's readings against the site's earlier visits and other works' frames
"""
