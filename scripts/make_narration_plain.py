"""Rebuild the clean (unboosted) narration mix from tts_meta + storyboard.

Writes narration_plain.m4a: cover voice + per-scene edge-tts clips delayed onto
the scene timeline (cover offset included). This is the pristine source that
mix_audio.py boosts, so gain is never applied twice.
"""
import json
import os
import subprocess

from config import COVER_PAD, FFMPEG, FFPROBE, LEAD, PROJECT, WORK
from config import ensure_dirs
ensure_dirs()
OUT = str(WORK / "narration_plain.m4a")
LEAD = 0.55
COVER_DUR = 3.59   # must match assemble.py: tts cover dur (1.99) + 1.6 tail

with open(os.path.join(WORK, "tts_meta.json"), encoding="utf-8") as f:
    tts = json.load(f)
with open(os.path.join(PROJECT, "storyboard.16x9.json"), encoding="utf-8") as f:
    sb = json.load(f)

durs = {s["id"]: s["dur"] for s in tts["scenes"]}
mp3s = {s["id"]: s["mp3"] for s in tts["scenes"]}

inputs = [FFMPEG, "-y", "-i", tts["cover"]["mp3"]]
parts = []
cursor = 0.0
idx = 1  # input 0 is the cover voice; scenes follow as 1..N

for scene in sb["scenes"]:
    sid = scene["id"]
    start = cursor + LEAD + COVER_DUR
    inputs += ["-i", mp3s[sid]]
    d = int(round(start * 1000))
    label = len(parts) + 1
    parts.append("[%d:a]adelay=%d|%d[a%d]" % (idx, d, d, label))
    idx += 1
    cursor += scene["duration_sec"]

total = round(COVER_DUR + cursor, 3)
labels = "".join("[a%d]" % (i + 1) for i in range(len(parts)))
mix_in = "[0:a]" + labels
graph = ";".join(parts) + ";" + \
    "%samix=inputs=%d:duration=longest:dropout_transition=0," \
    "apad,atrim=0:%.3f[aout]" % (mix_in, len(parts) + 1, total)

run = subprocess.run(
    inputs + ["-filter_complex", graph, "-map", "[aout]",
              "-c:a", "aac", "-b:a", "192k", "-ar", "48000", OUT],
    capture_output=True, text=True)
if run.returncode != 0:
    raise SystemExit("narration rebuild failed:\n" + run.stderr[-3000:])

d = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", OUT],
                   capture_output=True, text=True, check=True)
print("narration_plain ->", OUT, "%.2fs" % float(d.stdout.strip()))
