#!/usr/bin/env python3
"""Index, decode-check and montage the v3 video clips (CPU; imageio + imageio-ffmpeg + Pillow).

    python scripts/v3_video_index.py --videos <runs>/videos --plans configs/v3/video --output <runs>/videos

For every entry of configs/v3/video/plan_*.json (in the frozen rule order: main comparison, clean baseline,
severe noise, giver-reference comparison) it requires the MP4 and its sidecar, decodes every frame, checks the
decoded frame count against the sidecar, and records size/SHA-256, motion (mean absolute frame difference) and
the evaluation vs replay outcome. Writes video_index.json and montage.mp4 (all clips in rule order, real-time
20 Hz playback, a caption bar with category/method/run/case/outcome, and a 1 s title card per clip).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ORDER = ["main_comparison", "clean_baseline", "severe_noise", "giver_reference_comparison"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def caption(frame: np.ndarray, lines: list[str]) -> np.ndarray:
    from PIL import Image, ImageDraw, ImageFont

    h, w = frame.shape[:2]
    bar = 22 * len(lines) + 10
    img = Image.new("RGB", (w, h + bar), (20, 24, 36))
    img.paste(Image.fromarray(frame), (0, 0))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    for i, t in enumerate(lines):
        d.text((10, h + 6 + 22 * i), t, fill=(235, 235, 235), font=font)
    return np.asarray(img)


def card(w: int, h: int, lines: list[str]) -> np.ndarray:
    blank = np.full((h, w, 3), 245, np.uint8)
    from PIL import Image, ImageDraw, ImageFont

    img = Image.fromarray(blank)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    for i, t in enumerate(lines):
        d.text((40, h // 2 - 20 * len(lines) + 40 * i), t, fill=(20, 24, 36), font=font)
    return np.asarray(img)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--videos", required=True)
    ap.add_argument("--plans", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    import imageio.v2 as imageio

    V, O = Path(a.videos), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    entries = []
    for name in ("common", "raw", "filtered"):
        for e in json.loads((Path(a.plans) / f"plan_{name}.json").read_text()):
            entries.append({**e, "recording_process": f"plan_{name}"})
    entries.sort(key=lambda e: ORDER.index(e["category"]))
    clips, problems = [], []
    for e in entries:
        mp4 = V / Path(e["output"]).name
        side = mp4.with_suffix(".json")
        if not mp4.exists() or not side.exists():
            problems.append(f"missing {mp4.name} or its sidecar")
            continue
        s = json.loads(side.read_text())
        frames = [f for f in imageio.get_reader(mp4)]
        motion = float(np.mean([np.abs(frames[i + 1].astype(np.int16) - frames[i].astype(np.int16)).mean()
                                for i in range(len(frames) - 1)])) if len(frames) > 1 else 0.0
        if len(frames) != s.get("frames"):
            problems.append(f"{mp4.name}: decoded {len(frames)} frames, sidecar says {s.get('frames')}")
        if motion <= 0.0:
            problems.append(f"{mp4.name}: no motion")
        clips.append({"video": mp4.name, "category": e["category"], "method": e["method"], "run_id": e["run_id"],
                      "case_id": e["case_id"], "checkpoint": Path(e["checkpoint"]).name if e.get("checkpoint") else None,
                      "overrides": e.get("overrides", {}), "recording_process": e["recording_process"],
                      "bytes": mp4.stat().st_size, "sha256": sha(mp4), "sidecar": side.name, "sidecar_sha256": sha(side),
                      "decoded_frames": len(frames), "resolution": list(frames[0].shape[1::-1]) if frames else None,
                      "fps": s.get("fps"), "playback_speed": s.get("playback_speed"),
                      "mean_abs_frame_diff": round(motion, 3),
                      "evaluation_outcome": s.get("evaluation_outcome"), "replay_outcome": s.get("replay_outcome"),
                      "replay_matches_evaluation": s.get("replay_matches_evaluation"),
                      "checkpoint_sha256": s.get("checkpoint_sha256") or s.get("evaluation_checkpoint_sha256"),
                      "camera_eye_m": s.get("camera_eye_m"), "camera_target_m": s.get("camera_target_m"),
                      "source_commit": (s.get("git") or {}).get("commit"), "source_dirty": (s.get("git") or {}).get("dirty"), "config_hash": s.get("config_hash"),
                      "controller_hash": s.get("controller_hash"), "suite_hash": s.get("suite_hash")})
        e["_frames"] = frames
    if problems:
        (O / "video_index_problems.json").write_text(json.dumps(problems, indent=1) + "\n")
        raise SystemExit("\n".join(problems))
    w = max(c["resolution"][0] for c in clips)
    mont = []
    for c, e in zip(clips, entries):
        ev, rp = c["evaluation_outcome"] or {}, c["replay_outcome"] or {}
        title = [c["category"].replace("_", " "), f"{c['run_id']}  ({c['method']})", f"case {c['case_id']}",
                 f"evaluation: {ev.get('terminal_reason')}   replay: {rp.get('terminal_reason')}"]
        f0 = e["_frames"][0]
        mont += [card(f0.shape[1], f0.shape[0] + 98, title)] * int(c["fps"] or 20)
        cap = [f"{c['category']} | {c['run_id']} | {c['case_id']}",
               f"eval {ev.get('terminal_reason')} | replay {rp.get('terminal_reason')} | 20 Hz control, real time",
               "synthetic translation sensor in simulation (not vision, not sim-to-real)",
               f"source {str(c['source_commit'])[:10]} ckpt {str(c['checkpoint'] or '-')}"]
        mont += [caption(f, cap) for f in e["_frames"]]
        assert mont[-1].shape[1] == w
    imageio.mimwrite(O / "montage.mp4", mont, fps=20, codec="libx264", quality=8, macro_block_size=8)
    mframes = sum(1 for _ in imageio.get_reader(O / "montage.mp4"))
    idx = {"rule": "configs/v3/video_rule.json", "selection": "configs/v3/video/selection.json", "clips": clips,
           "distinct_clips": len(clips), "distinct_cases": len({c["case_id"] for c in clips}),
           "replay_disagreements": [c["video"] for c in clips if c["replay_matches_evaluation"] is False],
           "montage": {"file": "montage.mp4", "bytes": (O / "montage.mp4").stat().st_size, "sha256": sha(O / "montage.mp4"),
                       "frames": mframes, "fps": 20, "seconds": round(mframes / 20, 1)}}
    (O / "video_index.json").write_text(json.dumps(idx, indent=1) + "\n")
    print(json.dumps({"clips": len(clips), "montage_s": idx["montage"]["seconds"],
                      "replay_disagreements": idx["replay_disagreements"]}, indent=1))


if __name__ == "__main__":
    main()
