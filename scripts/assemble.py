"""Assemble the final 16:9 video: cover + narrated scenes + burned subtitles."""
import json
import os
import subprocess

from config import (FFMPEG, FFPROBE, FPS, HEIGHT, LEAD, PROJECT, TAIL,
                    WIDTH, WORK, ensure_dirs, final_video_path)
ensure_dirs()
SILENT = str(PROJECT / "out" / "story_16x9_silent.mp4")
COVER = str(WORK / "cover_16x9.png")
FINAL = str(final_video_path())

LEAD = LEAD

with open(os.path.join(WORK, "tts_meta.json"), encoding="utf-8") as f:
    tts = json.load(f)
with open(os.path.join(PROJECT, "storyboard.16x9.json"), encoding="utf-8") as f:
    sb = json.load(f)

scenes = {s["id"]: s for s in sb["scenes"]}


def dur(path):
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


# ---------- build the narration audio track on the scene timeline ----------
# The rendered video starts at scene 01 t=0. Cover is prepended afterwards.
audio_parts = []
cursor = 0.0
timeline = []

for s in sb["scenes"]:
    sid = s["id"]
    scene_dur = s["duration_sec"]
    speech = next(x["dur"] for x in tts["scenes"] if x["id"] == sid)
    mp3 = next(x["mp3"] for x in tts["scenes"] if x["id"] == sid)
    start = cursor + LEAD
    timeline.append({"id": sid, "start": round(start, 3),
                     "end": round(start + speech, 3), "text": s["text"]})
    audio_parts.append((mp3, start))
    cursor += scene_dur

total_scene = cursor

# ---------- concat cover + silent video ----------
cover_dur = round(tts["cover"]["dur"] + 1.6, 3)   # title voice + a beat
stage = os.path.join(WORK, "stage.mp4")

run = subprocess.run([
    FFMPEG, "-y",
    "-loop", "1", "-t", str(cover_dur), "-i", COVER,
    "-i", SILENT,
    "-filter_complex",
    "[0:v]scale=1920:1080,fps=30,format=yuv420p[cv];"
    "[1:v]fps=30,format=yuv420p[sv];"
    "[cv][sv]concat=n=2:v=1:a=0[v]",
    "-map", "[v]",
    "-c:v", "libx264", "-crf", "18", "-preset", "medium",
    stage,
], capture_output=True, text=True)
if run.returncode != 0:
    raise SystemExit("concat failed:\n" + run.stderr[-3000:])

stage_dur = dur(stage)
print("staged video: %.2fs (cover %.2fs + scenes %.2fs)" % (
    stage_dur, cover_dur, total_scene))

# ---------- build audio: cover voice + scene narration, mixed ----------
# NB: the final video is the COVER followed by the scenes, so every scene
# narration must be delayed by cover_dur to stay in sync with the picture.
mix_inputs = [FFMPEG, "-y", "-i", tts["cover"]["mp3"]]
for mp3, _ in audio_parts:
    mix_inputs += ["-i", mp3]

# delay each scene narration to its absolute start (cover offset included)
filters = []
for i, (mp3, start) in enumerate(audio_parts, start=1):
    delay = int(round((start + cover_dur) * 1000))
    filters.append("[%d:a]adelay=%d|%d[a%d]" % (i, delay, delay, i))

labels = "".join("[a%d]" % i for i in range(1, len(audio_parts) + 1))
mix_map = "[0:a]" + "".join("[a%d]" % i for i in range(1, len(audio_parts) + 1))
# pad with silence and trim to the exact staged-video length
filters.append(
    "%samix=inputs=%d:duration=longest:dropout_transition=0,"
    "apad,atrim=0:%.3f[aout]" % (mix_map, len(audio_parts) + 1, stage_dur))

audio_path = os.path.join(WORK, "narration.m4a")
run = subprocess.run(
    mix_inputs + ["-filter_complex", ";".join(filters),
                  "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", audio_path],
    capture_output=True, text=True)
if run.returncode != 0:
    raise SystemExit("audio mix failed:\n" + run.stderr[-3000:])

print("audio built: %.2fs (target %.2fs)" % (dur(audio_path), stage_dur))

# ---------- SRT (absolute timeline incl. cover offset) ----------
def srt_ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)

srt_path = os.path.join(WORK, "subtitles.srt")
with open(srt_path, "w", encoding="utf-8") as f:
    for n, item in enumerate(timeline, start=1):
        f.write("%d\n%s --> %s\n%s\n\n" % (
            n, srt_ts(item["start"] + cover_dur),
            srt_ts(item["end"] + cover_dur),
            item["text"].replace("\n", " ")))

print("srt written: %d cues" % len(timeline))

# ---------- final mux: video + audio ----------
# The Remotion render already burns each beat's text into the left caption
# column, so we do NOT overlay the SRT here: a bottom subtitle would duplicate
# the caption and overlap the artwork panel. The .srt is still written next to
# the video as an optional external subtitle track.
os.chdir(WORK)
run = subprocess.run([
    FFMPEG, "-y",
    "-i", stage,
    "-i", audio_path,
    "-map", "0:v", "-map", "1:a",
    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    FINAL,
], capture_output=True, text=True)
if run.returncode != 0:
    raise SystemExit("final mux failed:\n" + run.stderr[-4000:])

print("FINAL ->", FINAL)
print("duration: %.2fs" % dur(FINAL))
