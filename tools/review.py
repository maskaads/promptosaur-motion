#!/usr/bin/env python3
"""Look at a render the way a reviewer does, before you say it is done.

  sheet   8 frames per shot in one image per shot, each frame labelled with
          its frame number and time. Open the images and look at them.
  frames  measures every sampled frame: empty, too dark, burned to white,
          frozen picture.
  final   checks the finished file: it exists, decodes without errors, has
          the right length, size and frame rate, has sound, and how loud it is.

Usage:
  python review.py sheet  draft.mp4|frames/ [--timeline timeline.json | --every 2.5] [--out sheets]
  python review.py frames draft.mp4|frames/ [--step 0.5]
  python review.py final  final.mp4 [--duration 15] [--size 1920x1080] [--fps 30]

Needs: pip install pillow numpy, and ffmpeg + ffprobe on PATH.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# no console window per child process on Windows
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}


# ---------- frame access: a video file or a folder of numbered images ----------

class Source:
    def __init__(self, path, fps=None):
        self.path = path
        self.is_dir = os.path.isdir(path)
        if self.is_dir:
            self.files = sorted(f for f in os.listdir(path) if re.search(r"\.(png|jpe?g)$", f, re.I))
            if not self.files:
                sys.exit(f"no frames in {path}")
            self.fps = fps or 30
            self.duration = len(self.files) / self.fps
        else:
            info = probe(path)
            v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
            if not v:
                sys.exit(f"no video stream in {path}")
            num, den = v["r_frame_rate"].split("/")
            self.fps = fps or float(num) / float(den)
            self.duration = float(info["format"]["duration"])

    @property
    def frames(self):
        return len(self.files) if self.is_dir else int(round(self.duration * self.fps))

    def get(self, f):
        f = max(0, min(self.frames - 1, f))
        if self.is_dir:
            return Image.open(os.path.join(self.path, self.files[f])).convert("RGB")
        for back in range(4):  # seeking to the very last frame can return nothing; step back
            t = max(0.0, (f - back) / self.fps)
            png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", self.path, "-frames:v", "1",
                                  "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, **NOWIN).stdout
            if png:
                return Image.open(io.BytesIO(png)).convert("RGB")
        return None


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, text=True, **NOWIN)
    if r.returncode != 0:
        sys.exit(f"ffprobe cannot read {path}: {r.stderr.strip()}")
    return json.loads(r.stdout)


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# ---------- sheet ----------

def cmd_sheet(a):
    src = Source(a.input, a.fps)
    os.makedirs(a.out, exist_ok=True)
    shots = []
    if a.timeline:
        tl = json.load(open(a.timeline, encoding="utf-8"))
        shots = [(s.get("id", f"shot{i + 1}"), s["start"], s["end"]) for i, s in enumerate(tl.get("shots", []))]
    if not shots:
        step = a.every
        t, i = 0.0, 1
        while t < src.duration - 1e-6:
            shots.append((f"part{i}", t, min(src.duration, t + step)))
            t += step
            i += 1
    tw = 480
    for sid, s, e in shots:
        f0, f1 = int(round(s * src.fps)), max(int(round(e * src.fps)) - 1, int(round(s * src.fps)))
        picks = [int(round(f0 + (f1 - f0) * k / 7)) for k in range(8)]
        tiles = []
        for f in picks:
            im = src.get(f)
            if im is None:
                im = Image.new("RGB", (16, 9), "red")
            im = im.resize((tw, int(tw * im.height / im.width)))
            d = ImageDraw.Draw(im)
            label = f"{sid}  f{f}  {f / src.fps:.2f}s"
            d.rectangle([0, 0, 8 + 9 * len(label), 24], fill=(0, 0, 0))
            d.text((5, 3), label, fill=(255, 210, 63), font=font(16))
            tiles.append(im)
        th = tiles[0].height
        sheet = Image.new("RGB", (tw * 4 + 5 * 4, th * 2 + 4 * 3), (40, 40, 40))
        for k, im in enumerate(tiles):
            sheet.paste(im, (4 + (k % 4) * (tw + 4), 4 + (k // 4) * (th + 4)))
        out = os.path.join(a.out, f"sheet_{sid}.png")
        sheet.save(out)
        print(out)


# ---------- frames ----------

def cmd_frames(a):
    src = Source(a.input, a.fps)
    step = max(1, int(round(a.step * src.fps)))
    problems, prev, still_since = [], None, None
    n = 0
    for f in range(0, src.frames, step):
        im = src.get(f)
        if im is None:
            problems.append((f, "UNREADABLE", "frame does not decode"))
            continue
        n += 1
        y = np.asarray(im.convert("L").resize((320, int(320 * im.height / im.width))), dtype=np.float32)
        mean, std, top = y.mean(), y.std(), np.percentile(y, 99.98)
        blown = (y >= 250).mean() * 100
        t = f / src.fps
        if std < a.empty_std:
            problems.append((f, "EMPTY", f"almost one flat color (mean {mean:.0f}, spread {std:.1f})"))
        elif top < a.dark:
            problems.append((f, "DARK", f"even the brightest pixels reach only {top:.0f} of 255; faces and text get lost"))
        if blown > a.blown:
            problems.append((f, "BURNED", f"{blown:.1f}% of the picture is pure white"))
        if prev is not None and np.abs(y - prev).mean() < 0.3:
            still_since = still_since if still_since is not None else f - step
            if (f - still_since) / src.fps > a.frozen:
                problems.append((f, "FROZEN", f"picture has not changed since frame {still_since} ({(f - still_since) / src.fps:.1f} s)"))
                still_since = f
        else:
            still_since = None
        prev = y
    for f, kind, msg in problems:
        print(f"frame {f:>6}  {f / src.fps:7.2f}s  {kind:<10} {msg}")
    print(f"{n} frames measured, {len(problems)} problems")
    sys.exit(1 if problems else 0)


# ---------- final ----------

def cmd_final(a):
    errors, info = [], []
    if not os.path.exists(a.input) or os.path.getsize(a.input) == 0:
        print(f"ERROR  {a.input} is missing or empty")
        sys.exit(1)
    p = probe(a.input)
    v = next((s for s in p["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    dur = float(p["format"].get("duration", 0))
    info.append(f"length {dur:.2f} s, {os.path.getsize(a.input) / 1e6:.1f} MB")
    if not v:
        errors.append("no video stream")
    else:
        num, den = v["r_frame_rate"].split("/")
        fps = float(num) / float(den)
        info.append(f"video {v['codec_name']} {v['width']}x{v['height']} {fps:g} fps {v.get('pix_fmt', '')}")
        if a.size and f"{v['width']}x{v['height']}" != a.size:
            errors.append(f"size {v['width']}x{v['height']}, expected {a.size}")
        if a.fps and abs(fps - a.fps) > 0.01:
            errors.append(f"{fps:g} fps, expected {a.fps:g}")
        if v.get("pix_fmt") not in (None, "yuv420p"):
            errors.append(f"pixel format {v.get('pix_fmt')}: many players and phones need yuv420p")
    if a.duration and abs(dur - a.duration) > 0.1:
        errors.append(f"length {dur:.2f} s, expected {a.duration:g} s")
    if not au:
        errors.append("no sound")
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", a.input, "-f", "null", "-"], capture_output=True, text=True, **NOWIN)
    if dec.returncode != 0 or dec.stderr.strip():
        errors.append("decode errors: " + dec.stderr.strip()[:300])
    if au:
        r = subprocess.run(["ffmpeg", "-nostats", "-i", a.input, "-af", "ebur128=framelog=quiet:peak=true", "-f", "null", "-"],
                           capture_output=True, text=True, **NOWIN)
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
        if m:
            lufs = float(m[-1])
            info.append(f"loudness {lufs:.1f} LUFS" + (f", true peak {tp[-1]} dBFS" if tp else ""))
            if lufs < -16 or lufs > -12:
                errors.append(f"loudness {lufs:.1f} LUFS; aim for -14 (YouTube and most platforms)")
            if not tp:
                errors.append("true peak was not measured")
            elif float(tp[-1]) > -1.0:
                errors.append(f"true peak {tp[-1]} dBFS; keep it at -1 or lower. AAC adds about 1.5 dB, so aim for -2.5 in the mix before encoding")
    for s in info:
        print("INFO  ", s)
    for s in errors:
        print("ERROR ", s)
    print("OK" if not errors else f"{len(errors)} problems")
    sys.exit(1 if errors else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("input")
    s.add_argument("--timeline")
    s.add_argument("--every", type=float, default=2.5)
    s.add_argument("--out", default="sheets")
    s.add_argument("--fps", type=float)
    s.set_defaults(fn=cmd_sheet)
    f = sub.add_parser("frames")
    f.add_argument("input")
    f.add_argument("--step", type=float, default=0.5, help="seconds between measured frames")
    f.add_argument("--fps", type=float)
    f.add_argument("--dark", type=float, default=90, help="brightest pixels (top 0.02%%) below this count as too dark")
    f.add_argument("--blown", type=float, default=6, help="percent of pure white that counts as burned")
    f.add_argument("--empty-std", type=float, default=4)
    f.add_argument("--frozen", type=float, default=3, help="seconds without change that count as frozen")
    f.set_defaults(fn=cmd_frames)
    n = sub.add_parser("final")
    n.add_argument("input")
    n.add_argument("--duration", type=float)
    n.add_argument("--size")
    n.add_argument("--fps", type=float)
    n.set_defaults(fn=cmd_final)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
