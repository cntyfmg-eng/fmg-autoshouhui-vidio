"""Generate edge-tts narration for every scene and measure real durations."""
import asyncio
import json
import os
import subprocess

from config import (FFPROBE, PITCH, PROJECT, RATE, TTS_DIR, TITLE,
                    VOICE, WORK, ensure_dirs)
ensure_dirs()

os.makedirs(TTS_DIR, exist_ok=True)

with open(os.path.join(PROJECT, "storyboard.json"), encoding="utf-8") as f:
    sb = json.load(f)

scenes = sb["scenes"]


def duration_of(path: str) -> float:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()), 3)


async def synth_one(scene):
    sid = scene["id"]
    # newlines in `text` are only display wrapping -> strip for speech
    text = scene["text"].replace("\n", "").replace("\r", "").strip()
    mp3 = os.path.join(TTS_DIR, f"{sid}.mp3")
    comm = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await comm.save(mp3)
    return sid, text, mp3, duration_of(mp3)


async def main():
    results = []
    for scene in scenes:
        sid, text, mp3, dur = await synth_one(scene)
        results.append({"id": sid, "text": text, "mp3": mp3, "dur": dur})
        print(f"{sid}  {dur:6.2f}s  {text}", flush=True)
    total = sum(r["dur"] for r in results)
    print(f"\nTOTAL narration: {total:.2f}s over {len(results)} scenes")

    # cover page narration
    cover_text = TITLE
    cover_mp3 = os.path.join(TTS_DIR, "cover.mp3")
    comm = edge_tts.Communicate(cover_text, VOICE, rate=RATE, pitch=PITCH)
    await comm.save(cover_mp3)
    cover_dur = duration_of(cover_mp3)
    print(f"cover  {cover_dur:6.2f}s  {cover_text}")

    meta = {
        "voice": VOICE,
        "rate": RATE,
        "pitch": PITCH,
        "cover": {"mp3": cover_mp3, "dur": cover_dur, "text": cover_text},
        "scenes": results,
        "total_narration": round(total, 3),
    }
    with open(os.path.join(WORK, "tts_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("wrote tts_meta.json")


if __name__ == "__main__":
    import edge_tts
    asyncio.run(main())
