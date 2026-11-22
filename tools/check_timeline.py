#!/usr/bin/env python3
"""Check an animation schedule against the motion rules and the voice-over.

Keep every entrance, exit and camera move of the video in one file,
timeline.json, and drive the animation from it. Then this script can check
the rules before anything is rendered:

  - no two elements start on the same frame;
  - no linear moves (a slow camera drift may be marked "camera": true);
  - after a move the same element holds still at least 12 frames;
  - text stays on screen long enough to read (1 s per 3 words);
  - something new happens at least every 2.5 s;
  - with a voice-over (timing.json from align.py): every event with a "cue"
    starts on the frame of its word, and every spoken number has an event.

timeline.json:
{
  "fps": 30,
  "duration": 15,
  "events": [
    {"id": "title-in", "el": "title", "start": 12, "end": 30, "ease": "power3.out",
     "text": "PROMPTOSAUR"},
    {"id": "gap-label", "el": "label", "start": 517, "end": 532, "ease": "expo.out",
     "cue": "77", "text": "77 million years"},
    {"id": "drift", "el": "camera", "start": 0, "end": 450, "ease": "linear", "camera": true}
  ]
}
start and end are frame numbers. "cue" is the word as written in the script;
add "cue_n": 2 for its second occurrence. "visible_until" (frame) is optional
for text that stays after its move.

Usage:
  python check_timeline.py timeline.json [--timing timing.json] [--tol 0]
Exit code 1 if any error was found.
"""
import argparse
import json
import re
import sys
from collections import defaultdict


def norm(w):
    return re.sub(r"[^\w.%$]", "", w.lower()).strip(".")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("timeline")
    ap.add_argument("--timing")
    ap.add_argument("--tol", type=int, default=0, help="allowed distance from the cue frame, in frames")
    ap.add_argument("--max-gap", type=float, default=2.5, help="seconds without anything new")
    ap.add_argument("--hold", type=int, default=12, help="frames an element holds still between moves")
    a = ap.parse_args()

    tl = json.load(open(a.timeline, encoding="utf-8"))
    fps = tl.get("fps", 30)
    total = int(round(tl.get("duration", 0) * fps)) or None
    ev = sorted(tl["events"], key=lambda e: e["start"])
    errors, warns = [], []

    def name(e):
        return e.get("id") or e.get("el") or "?"

    # 1. same-frame starts
    by_start = defaultdict(list)
    for e in ev:
        by_start[e["start"]].append(name(e))
    for f, names in sorted(by_start.items()):
        if len(names) > 1:
            errors.append(f"frame {f}: {len(names)} elements start together ({', '.join(names)}); offset them by 2 to 4 frames")

    # 2. linear moves, 8. out of range, broken events
    for e in ev:
        if e.get("end", e["start"]) < e["start"]:
            errors.append(f"{name(e)}: ends before it starts")
        if total and e.get("end", e["start"]) > total:
            errors.append(f"{name(e)}: ends at frame {e['end']}, after the last frame {total}")
        ease = str(e.get("ease", "")).lower()
        if ease in ("", "linear", "none", "power0", "power0.none") and not e.get("camera"):
            errors.append(f"{name(e)}: linear or missing ease; use an ease-out (fast start, long settle)")

    # 3. hold between moves of the same element
    by_el = defaultdict(list)
    for e in ev:
        by_el[e.get("el", name(e))].append(e)
    for el, lst in by_el.items():
        for p, n in zip(lst, lst[1:]):
            if p.get("camera") or n.get("camera"):
                continue
            gap = n["start"] - p.get("end", p["start"])
            if gap < a.hold:
                errors.append(f"{el}: moves again {gap} frames after '{name(p)}' ends (frame {n['start']}); hold at least {a.hold}")

    # 4. reading time
    for el, lst in by_el.items():
        for i, e in enumerate(lst):
            if not e.get("text"):
                continue
            words = len(str(e["text"]).split())
            until = e.get("visible_until") or (lst[i + 1]["start"] if i + 1 < len(lst) else total)
            if until is None:
                continue
            shown = (until - e.get("end", e["start"])) / fps
            need = words / 3
            if shown + 1e-6 < need:
                warns.append(f"{name(e)}: '{e['text']}' is readable for {shown:.1f} s, needs {need:.1f} s ({words} words)")

    # 5. something new every max-gap seconds
    starts = sorted({e["start"] for e in ev if not e.get("camera")})
    if total:
        starts_end = starts + [total]
    else:
        starts_end = starts
    prev = 0
    for s in starts_end:
        if (s - prev) / fps > a.max_gap:
            warns.append(f"frames {prev} to {s}: nothing new for {(s - prev) / fps:.1f} s")
        prev = s

    # 6-7. voice-over sync
    if a.timing:
        tm = json.load(open(a.timing, encoding="utf-8"))
        words = tm["words"]
        if tm.get("fps") and tm["fps"] != fps:
            errors.append(f"timing.json is for {tm['fps']} fps, timeline is {fps} fps; run align.py with --fps {fps}")
        cued = set()
        for e in ev:
            if "cue" not in e:
                continue
            want, nth = norm(str(e["cue"])), int(e.get("cue_n", 1))
            hits = [w for w in words if norm(w["word"]) == want]
            if len(hits) < nth:
                errors.append(f"{name(e)}: cue '{e['cue']}' (occurrence {nth}) is not in timing.json")
                continue
            w = hits[nth - 1]
            cued.add(w["i"])
            d = e["start"] - w["frame"]
            if abs(d) > a.tol:
                side = "late" if d > 0 else "early"
                errors.append(f"{name(e)}: starts at frame {e['start']}, the word '{w['word']}' starts at frame {w['frame']} ({abs(d)} frames {side})")
        for w in words:
            if w.get("number") and w["i"] not in cued:
                errors.append(f"spoken number '{w['word']}' at frame {w['frame']} has no event on screen; add one with \"cue\": \"{w['word'].strip('.,')}\"")

    for m in errors:
        print("ERROR ", m)
    for m in warns:
        print("WARN  ", m)
    print(f"{len(ev)} events, {len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
