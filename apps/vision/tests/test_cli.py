"""The real path end to end, minus the network: a manifest, two videos on disk, `build`."""

import json

import numpy as np

from drishti_vision import manifest
from drishti_vision.cli import main
from drishti_vision.frames import write_video
from drishti_vision.synth import Site


def test_check_and_build(tmp_path, capsys):
    videos = tmp_path / "videos"
    videos.mkdir()
    rows = []
    for i, kind in enumerate(("masonry", "road")):
        frames = Site(kind, 20 + i, n_frames=30, size=(192, 256)).shot().frames
        write_video(str(videos / f"own-{kind}.mp4"), frames, fps=10)
        rows.append(manifest.Video(id=f"own-{kind}", url=f"file://{kind}", source="own",
                                   licence="own", attribution="", channel=f"team-{i}",
                                   work_type="road" if kind == "road" else "building",
                                   material=kind, country="IN", camera="fixed"))
    rows.append(manifest.Video(id="nd-1", url="https://example.org/x.mp4", source="other",
                               licence="cc-by-nd", attribution="X", channel="x",
                               work_type="building", material="masonry", country="IN",
                               camera="fixed"))
    m = tmp_path / "manifest.jsonl"
    manifest.save(m, rows)
    assert main(["check", str(m)]) == 1                     # the no-derivatives row
    assert "waits for the owner" in capsys.readouterr().out
    out = tmp_path / "data"
    code = main(["build", str(m), "--videos", str(videos), "--out", str(out),
                 "--backbone", "handcrafted", "--width", "256", "--frames", "30",
                 "--pairs", "12"])
    assert code == 0
    shots = [json.loads(x) for x in (out / "shots.jsonl").read_text().splitlines()]
    assert {s["video_id"] for s in shots} == {"own-masonry", "own-road"}
    assert all(s["licence"] == "own" for s in shots)
    folds = json.loads((out / "folds.json").read_text())["leave_one_type_out"]
    assert set(folds) == {"masonry", "road"}
    with np.load(out / "labels" / f"{shots[0]['shot_id']}.npz") as z:
        assert len(z["label"]) > 0
