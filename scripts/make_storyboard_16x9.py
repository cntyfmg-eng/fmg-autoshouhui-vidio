"""Build a 16:9 storyboard whose per-scene durations follow the real narration length."""
import json
import os

from config import FPS, HEIGHT, PROJECT, WIDTH, WORK, ensure_dirs
ensure_dirs()

with open(os.path.join(PROJECT, "storyboard.json"), encoding="utf-8") as f:
    sb = json.load(f)
with open(os.path.join(WORK, "tts_meta.json"), encoding="utf-8") as f:
    tts = json.load(f)

durs = {s["id"]: s["dur"] for s in tts["scenes"]}

FPS = 30
LEAD = 0.55     # small silence before each line so it doesn't start abruptly
TAIL = 1.15    # breathing room after each line

for scene in sb["scenes"]:
    speech = durs[scene["id"]]
    scene["duration_sec"] = round(speech + LEAD + TAIL, 3)
    # narration field drives the audio track; keep display text wrapping as-is
    scene["narration"] = scene["text"].replace("\n", "").strip()

p = sb["project"]
p["width"] = 1920
p["height"] = 1080
p["export_size"] = [1920, 1080]
p["ratio"] = "16:9"
p["layout_16x9"] = True

total = sum(s["duration_sec"] for s in sb["scenes"])
sb["total_duration_sec"] = round(total, 3)

out = os.path.join(PROJECT, "storyboard.16x9.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(sb, f, ensure_ascii=False, indent=2)

print("scenes:", len(sb["scenes"]))
print("total duration: %.2fs (%d frames @ %dfps)" % (total, round(total * FPS), FPS))
print("wrote", out)
for s in sb["scenes"][:5]:
    print(" ", s["id"], s["duration_sec"], s["text"].replace("\n", ""))
